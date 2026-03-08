"""基于规则的 Safety reviewer。"""

from __future__ import annotations

import json
import re
from typing import Any

from agent_forge.components.protocol import FinalAnswer, ToolCall
from agent_forge.components.safety.domain import (
    SafetyAction,
    SafetyCheckRequest,
    SafetyDecision,
    SafetyReviewer,
    SafetyRule,
    SafetyRuleMatch,
)


class _BaseRuleBasedReviewer(SafetyReviewer):
    """规则审查器基类。"""

    reviewer_version = "rules-v1"
    policy_version = "v1"

    def __init__(self, *, rules: list[SafetyRule] | None = None) -> None:
        """初始化规则审查器。

        Args:
            rules: 可选规则覆盖列表。
        """

        self.rules = rules or self._default_rules()

    def review(self, request: SafetyCheckRequest) -> SafetyDecision:
        """执行规则审查。

        Args:
            request: 标准化审查请求。

        Returns:
            SafetyDecision: 结构化决策。
        """

        matches, evidence = self._match_rules(request)
        action = _select_action(matches)
        allowed = action == "allow"
        reason = "通过安全审查"
        if matches:
            reason = "；".join(match.reason for match in matches if match.reason) or "命中安全规则"
        return SafetyDecision(
            allowed=allowed,
            action=action,
            stage=self.stage,
            reason=reason,
            reviewer_name=self.reviewer_name,
            reviewer_version=self.reviewer_version,
            policy_version=self.policy_version,
            triggered_rules=matches,
            evidence=evidence,
            metadata={"rule_count": len(matches)},
        )

    def _match_rules(self, request: SafetyCheckRequest) -> tuple[list[SafetyRuleMatch], list[str]]:
        """逐条匹配规则。

        Args:
            request: 标准化请求。

        Returns:
            tuple[list[SafetyRuleMatch], list[str]]: 命中规则与脱敏证据。
        """

        raise NotImplementedError

    def _default_rules(self) -> list[SafetyRule]:
        """返回默认规则列表。

        Returns:
            list[SafetyRule]: 默认规则。
        """

        raise NotImplementedError


class RuleBasedInputReviewer(_BaseRuleBasedReviewer):
    """输入阶段规则审查器。"""

    reviewer_name = "rule_based_input_reviewer"
    stage = "input"

    def _default_rules(self) -> list[SafetyRule]:
        """构建默认输入规则。"""

        return [
            SafetyRule(
                rule_id="input_prompt_injection",
                name="输入越权绕过",
                stage="input",
                severity="high",
                action="deny",
                description="尝试忽略系统提示或绕过限制",
                config={"keywords": ["忽略之前", "绕过限制", "bypass", "prompt injection", "越狱"]},
            ),
            SafetyRule(
                rule_id="input_high_risk_professional",
                name="高风险专业建议",
                stage="input",
                severity="critical",
                action="handoff",
                description="需要人工或专业人士复核的高风险问题",
                config={"keywords": ["处方药", "诊断", "保证收益", "必胜诉", "逃税", "炸弹"]},
            ),
        ]

    def _match_rules(self, request: SafetyCheckRequest) -> tuple[list[SafetyRuleMatch], list[str]]:
        text = request.task_input
        matches: list[SafetyRuleMatch] = []
        evidence: list[str] = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            keyword = _first_keyword_hit(text, rule.config.get("keywords", []))
            if keyword is None:
                continue
            matches.append(
                SafetyRuleMatch(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    action=rule.action,
                    reason=f"输入命中关键词: {keyword}",
                )
            )
            evidence.append(_snippet(text, keyword))
        return matches, _dedupe(evidence)


class RuleBasedToolReviewer(_BaseRuleBasedReviewer):
    """工具阶段规则审查器。"""

    reviewer_name = "rule_based_tool_reviewer"
    stage = "tool"

    def _default_rules(self) -> list[SafetyRule]:
        """构建默认工具规则。"""

        return [
            SafetyRule(
                rule_id="tool_high_side_effect_without_approval",
                name="高副作用工具缺少审批能力",
                stage="tool",
                severity="critical",
                action="deny",
                description="高副作用工具必须显式授权",
                config={"required_capability": "safety:tool:high_risk"},
            ),
            SafetyRule(
                rule_id="tool_destructive_name_guard",
                name="破坏性工具名拦截",
                stage="tool",
                severity="high",
                action="deny",
                description="名称明显具有删除或重置倾向的工具默认拒绝",
                config={"keywords": ["delete", "drop", "truncate", "reset", "wipe"]},
            ),
        ]

    def _match_rules(self, request: SafetyCheckRequest) -> tuple[list[SafetyRuleMatch], list[str]]:
        if request.tool_call is None:
            raise ValueError("tool 阶段必须提供 tool_call")
        tool_call = request.tool_call
        tool_spec = request.context.get("tool_spec", {}) or {}
        capabilities = set(request.context.get("capabilities", []))
        matches: list[SafetyRuleMatch] = []
        evidence: list[str] = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            if rule.rule_id == "tool_high_side_effect_without_approval":
                if tool_spec.get("side_effect_level") == "high" and rule.config["required_capability"] not in capabilities:
                    matches.append(
                        SafetyRuleMatch(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            action=rule.action,
                            reason="高副作用工具缺少审批能力",
                        )
                    )
                    evidence.append(_render_tool_evidence(tool_call=tool_call, tool_spec=tool_spec))
            elif rule.rule_id == "tool_destructive_name_guard":
                keyword = _first_keyword_hit(tool_call.tool_name, rule.config.get("keywords", []))
                if keyword is not None:
                    matches.append(
                        SafetyRuleMatch(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            action=rule.action,
                            reason=f"工具名命中高风险关键词: {keyword}",
                        )
                    )
                    evidence.append(_render_tool_evidence(tool_call=tool_call, tool_spec=tool_spec))
        return matches, _dedupe(evidence)


class RuleBasedOutputReviewer(_BaseRuleBasedReviewer):
    """输出阶段规则审查器。"""

    reviewer_name = "rule_based_output_reviewer"
    stage = "output"

    def _default_rules(self) -> list[SafetyRule]:
        """构建默认输出规则。"""

        return [
            SafetyRule(
                rule_id="output_illegal_instruction",
                name="违法危险指令输出",
                stage="output",
                severity="critical",
                action="deny",
                description="输出中出现明显违法危险操作指南",
                config={"keywords": ["制造炸弹", "爆炸物配方", "绕过监管"]},
            ),
            SafetyRule(
                rule_id="output_unbounded_guarantee",
                name="不受约束的确定性承诺",
                stage="output",
                severity="high",
                action="downgrade",
                description="输出中出现 100% 或绝对保证式表达",
                config={"keywords": ["100% 保证", "保证收益", "一定胜诉", "绝对安全"]},
            ),
            SafetyRule(
                rule_id="output_requires_handoff",
                name="需要人工复核的专业结论",
                stage="output",
                severity="critical",
                action="handoff",
                description="输出直接给出高风险专业结论且缺少转人工提示",
                config={"keywords": ["自行服用处方药", "无需律师", "无需医生"]},
            ),
        ]

    def _match_rules(self, request: SafetyCheckRequest) -> tuple[list[SafetyRuleMatch], list[str]]:
        answer = request.final_answer or FinalAnswer(status="failed", summary="", output={})
        text = _render_final_answer(answer)
        matches: list[SafetyRuleMatch] = []
        evidence: list[str] = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            keyword = _first_keyword_hit(text, rule.config.get("keywords", []))
            if keyword is None:
                continue
            matches.append(
                SafetyRuleMatch(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    action=rule.action,
                    reason=f"输出命中关键词: {keyword}",
                )
            )
            evidence.append(_snippet(text, keyword))
        return matches, _dedupe(evidence)


def _select_action(matches: list[SafetyRuleMatch]) -> SafetyAction:
    """从命中规则中选择最终动作。

    Args:
        matches: 命中规则列表。

    Returns:
        SafetyAction: 最终动作。
    """

    if not matches:
        return "allow"
    priority = {"deny": 4, "handoff": 3, "downgrade": 2, "allow": 1}
    selected = max(matches, key=lambda item: priority[item.action])
    return selected.action


def _first_keyword_hit(text: str, keywords: list[str]) -> str | None:
    """返回首个命中的关键词。

    Args:
        text: 待匹配文本。
        keywords: 关键词列表。

    Returns:
        str | None: 首个命中的关键词。
    """

    lowered = text.lower()
    for keyword in keywords:
        if keyword.lower() in lowered:
            return keyword
    return None


def _snippet(text: str, keyword: str) -> str:
    """抽取关键词附近的脱敏片段。

    Args:
        text: 原始文本。
        keyword: 命中关键词。

    Returns:
        str: 脱敏后的片段。
    """

    lower_text = text.lower()
    index = lower_text.find(keyword.lower())
    if index < 0:
        return _redact_text(text[:40])
    start = max(index - 12, 0)
    end = min(index + len(keyword) + 12, len(text))
    return _redact_text(text[start:end])


def _render_tool_evidence(*, tool_call: ToolCall, tool_spec: dict[str, Any]) -> str:
    """渲染工具证据。

    Args:
        tool_call: 工具调用。
        tool_spec: 工具规格。

    Returns:
        str: 脱敏证据。
    """

    sensitive_fields = set(tool_spec.get("sensitive_fields", []))
    masked_args = {
        key: ("***" if key in sensitive_fields else value)
        for key, value in tool_call.args.items()
    }
    return _redact_text(
        json.dumps(
            {
                "tool_name": tool_call.tool_name,
                "args": masked_args,
                "side_effect_level": tool_spec.get("side_effect_level", "none"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def _render_final_answer(answer: FinalAnswer) -> str:
    """把 FinalAnswer 收敛为文本。

    Args:
        answer: 最终答案。

    Returns:
        str: 归一化文本。
    """

    return json.dumps(
        {
            "summary": answer.summary,
            "output": answer.output,
            "references": answer.references,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _redact_text(text: str) -> str:
    """对证据文本做最小脱敏。

    Args:
        text: 原始文本。

    Returns:
        str: 脱敏文本。
    """

    text = re.sub(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", "***@***", text)
    text = re.sub(r"\b\d{11}\b", "***", text)
    text = text.replace("secret", "***").replace("token", "***").replace("password", "***")
    return text


def _dedupe(items: list[str]) -> list[str]:
    """去重并保序。

    Args:
        items: 原始列表。

    Returns:
        list[str]: 去重后的列表。
    """

    output: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output
