"""Safety 运行时。"""

from __future__ import annotations

from agent_forge.components.protocol import FinalAnswer
from agent_forge.components.safety.domain import (
    SafetyAuditRecord,
    SafetyCheckRequest,
    SafetyDecision,
    SafetyReviewer,
)


class SafetyRuntime:
    """统一编排输入、工具、输出三阶段审查。"""

    def __init__(
        self,
        *,
        input_reviewer: SafetyReviewer | None = None,
        tool_reviewer: SafetyReviewer | None = None,
        output_reviewer: SafetyReviewer | None = None,
    ) -> None:
        """初始化 SafetyRuntime。

        Args:
            input_reviewer: 输入审查器。
            tool_reviewer: 工具审查器。
            output_reviewer: 输出审查器。
        """

        if input_reviewer is None or tool_reviewer is None or output_reviewer is None:
            from agent_forge.components.safety.infrastructure import (
                RuleBasedInputReviewer,
                RuleBasedOutputReviewer,
                RuleBasedToolReviewer,
            )

            input_reviewer = input_reviewer or RuleBasedInputReviewer()
            tool_reviewer = tool_reviewer or RuleBasedToolReviewer()
            output_reviewer = output_reviewer or RuleBasedOutputReviewer()
        self._input_reviewer = input_reviewer
        self._tool_reviewer = tool_reviewer
        self._output_reviewer = output_reviewer
        self._audit_records: list[SafetyAuditRecord] = []

    def check_input(self, request: SafetyCheckRequest) -> SafetyDecision:
        """执行输入预检。

        Args:
            request: 标准化安全请求。

        Returns:
            SafetyDecision: 审查结果。
        """

        return self._review(request=request, reviewer=self._input_reviewer, expected_stage="input")

    def check_tool_call(self, request: SafetyCheckRequest) -> SafetyDecision:
        """执行工具前置审查。

        Args:
            request: 标准化安全请求。

        Returns:
            SafetyDecision: 审查结果。
        """

        return self._review(request=request, reviewer=self._tool_reviewer, expected_stage="tool")

    def check_output(self, request: SafetyCheckRequest) -> SafetyDecision:
        """执行最终输出审查。

        Args:
            request: 标准化安全请求。

        Returns:
            SafetyDecision: 审查结果。
        """

        return self._review(request=request, reviewer=self._output_reviewer, expected_stage="output")

    def get_audit_records(self) -> list[SafetyAuditRecord]:
        """返回审计记录快照。

        Returns:
            list[SafetyAuditRecord]: 当前审计记录副本。
        """

        return list(self._audit_records)

    def _review(self, *, request: SafetyCheckRequest, reviewer: SafetyReviewer, expected_stage: str) -> SafetyDecision:
        """统一执行 reviewer 并持久化审计。

        Args:
            request: 标准化请求。
            reviewer: 具体审查器。
            expected_stage: 预期阶段名。

        Returns:
            SafetyDecision: 标准化决策。
        """

        if request.stage != expected_stage:
            raise ValueError(f"SafetyRuntime 阶段不匹配: expected={expected_stage}, got={request.stage}")

        # 1. 统一入口：三阶段都只接受 SafetyCheckRequest，避免未来换 reviewer 时改调用方。
        decision = reviewer.review(request)
        # 2. 审计留痕：无论放行还是拦截都记录，后续可被观测或评估链路读取。
        self._audit_records.append(_build_audit_record(request=request, decision=decision))
        # 3. 返回结构化结果：上游只关心 decision，不关心 reviewer 内部实现。
        return decision


def apply_output_safety(final_answer: FinalAnswer, decision: SafetyDecision) -> FinalAnswer:
    """按输出审查结果生成最终可返回答案。

    Args:
        final_answer: 原始最终答案。
        decision: 输出阶段安全决策。

    Returns:
        FinalAnswer: 原样答案或安全降级版答案。
    """

    if decision.stage != "output":
        raise ValueError("apply_output_safety 只接受 output 阶段决策")
    if decision.action == "allow":
        return final_answer

    # 1. 明确降级语义：不同动作映射为不同 status，避免调用方自行猜测。
    status = "partial" if decision.action in {"downgrade", "handoff"} else "failed"
    # 2. 保留结构化外壳：前端、Evaluator、日志仍能消费统一 FinalAnswer 契约。
    message = decision.reason or "输出已被安全策略拦截"
    # 3. 最小暴露：不把原始高风险内容继续透传给下游。
    return FinalAnswer(
        status=status,
        summary=message,
        output={
            "message": message,
            "safety_action": decision.action,
            "policy_version": decision.policy_version,
            "reviewer": decision.reviewer_name,
        },
        artifacts=final_answer.artifacts,
        references=[*final_answer.references, f"policy_version:{decision.policy_version}"],
    )


def _build_audit_record(*, request: SafetyCheckRequest, decision: SafetyDecision) -> SafetyAuditRecord:
    """构建审计记录。

    Args:
        request: 安全审查请求。
        decision: 审查决策。

    Returns:
        SafetyAuditRecord: 审计对象。
    """

    return SafetyAuditRecord(
        trace_id=request.trace_id or str(request.context.get("trace_id", "")),
        run_id=request.run_id or str(request.context.get("run_id", "")),
        stage=decision.stage,
        action=decision.action,
        triggered_rules=[match.rule_id for match in decision.triggered_rules],
        reason=decision.reason,
        evidence=decision.evidence,
        reviewer_name=decision.reviewer_name,
        reviewer_version=decision.reviewer_version,
        policy_version=decision.policy_version,
    )
