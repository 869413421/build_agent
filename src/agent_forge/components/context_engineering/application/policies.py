"""Context Engineering 裁剪策略。"""

from __future__ import annotations

from typing import Any

from agent_forge.components.context_engineering.domain import BudgetReport, CitationItem, ContextBudget
from agent_forge.components.context_engineering.infrastructure import CharTokenEstimator
from agent_forge.components.protocol import AgentMessage


class ConservativeTrimmingPolicy:
    """保守裁剪策略：优先保留指令与最新用户意图。"""

    def trim(
        self,
        *,
        system_prompt: str | None,
        messages: list[AgentMessage],
        tools: list[dict[str, Any]],
        citations: list[CitationItem],
        budget: ContextBudget,
        estimator: CharTokenEstimator,
    ) -> tuple[list[AgentMessage], list[dict[str, Any]], list[CitationItem], BudgetReport]:
        """按确定性优先级执行上下文裁剪。

        Args:
            system_prompt: 可选 system 提示词。
            messages: 候选消息列表。
            tools: 候选工具列表。
            citations: 候选引用列表。
            budget: 上下文预算策略。
            estimator: Token 估算器。

        Returns:
            tuple[list[AgentMessage], list[dict[str, Any]], list[CitationItem], BudgetReport]:
                保留后的消息、工具、引用以及预算报告。
        """

        # 1. 初始化预算账本与输入状态。
        available = budget.available_input_tokens
        kept_messages: dict[int, AgentMessage] = {}
        dropped_sections: list[str] = []
        used_tokens = estimator.estimate_text(system_prompt or "")
        latest_user_idx = _find_latest_user_index(messages)
        mandatory_indexes = {
            idx for idx, msg in enumerate(messages) if msg.role in {"system", "developer"}
        }
        if latest_user_idx is not None:
            mandatory_indexes.add(latest_user_idx)
        truncated_latest_user = False

        # 2. 先处理必保消息；预算紧张时改为截断而非丢弃。
        ordered_mandatory_indexes = sorted(mandatory_indexes)
        for position, idx in enumerate(ordered_mandatory_indexes):
            candidate = messages[idx].model_copy(deep=True)
            cost = estimator.estimate_message(candidate)
            remaining_mandatory = len(ordered_mandatory_indexes) - position - 1
            minimum_reserved_for_rest = remaining_mandatory * (estimator.message_overhead_tokens() + 1)
            remaining = max(0, available - used_tokens)
            allowed_for_current = max(1, remaining - minimum_reserved_for_rest)
            if cost <= remaining and (remaining - cost) >= minimum_reserved_for_rest:
                kept_messages[idx] = candidate
                used_tokens += cost
                continue
            content_budget = max(1, allowed_for_current - estimator.message_overhead_tokens())
            candidate.content = estimator.truncate_text(candidate.content, content_budget)
            kept_messages[idx] = candidate
            used_tokens = min(available, used_tokens + estimator.estimate_message(candidate))
            if latest_user_idx == idx:
                truncated_latest_user = True
                dropped_sections.append("latest_user_truncated")
            else:
                dropped_sections.append(f"mandatory_message_truncated:{idx}")

        # 3. 工具优先于可选历史消息。
        kept_tools: list[dict[str, Any]] = []
        tools_cost = sum(estimator.estimate_tool(item) for item in tools)
        if used_tokens + tools_cost <= available:
            kept_tools = [dict(item) for item in tools]
            used_tokens += tools_cost
        elif tools:
            dropped_sections.append("tools_dropped")

        # 4. 在剩余预算中按“新到旧”回填可选历史消息。
        optional_indexes = [idx for idx in range(len(messages) - 1, -1, -1) if idx not in mandatory_indexes]
        for idx in optional_indexes:
            candidate = messages[idx].model_copy(deep=True)
            cost = estimator.estimate_message(candidate)
            if used_tokens + cost > available:
                continue
            kept_messages[idx] = candidate
            used_tokens += cost

        # 5. 引用最后处理，并按“单条合成消息”估算，确保预算与最终载荷一致。
        kept_citations: list[CitationItem] = []
        if citations:
            citations_cost = estimator.estimate_citation_message(citations)
            if used_tokens + citations_cost <= available:
                kept_citations = [citation.model_copy(deep=True) for citation in citations]
                used_tokens += citations_cost
            else:
                dropped_sections.append("citations_dropped")

        ordered_messages = [kept_messages[idx] for idx in sorted(kept_messages.keys())]
        total_estimated = (
            estimator.estimate_text(system_prompt or "")
            + sum(estimator.estimate_message(item) for item in messages)
            + sum(estimator.estimate_tool(item) for item in tools)
            + (estimator.estimate_citation_message(citations) if citations else 0)
        )
        kept_estimated = (
            estimator.estimate_text(system_prompt or "")
            + sum(estimator.estimate_message(item) for item in ordered_messages)
            + sum(estimator.estimate_tool(item) for item in kept_tools)
            + (estimator.estimate_citation_message(kept_citations) if kept_citations else 0)
        )
        report = BudgetReport(
            available_tokens=available,
            total_estimated_tokens=total_estimated,
            kept_estimated_tokens=kept_estimated,
            dropped_estimated_tokens=max(0, total_estimated - kept_estimated),
            kept_messages=len(ordered_messages),
            dropped_messages=max(0, len(messages) - len(ordered_messages)),
            dropped_sections=_dedup_preserve_order(dropped_sections),
            truncated_latest_user=truncated_latest_user,
        )
        return ordered_messages, kept_tools, kept_citations, report


def _find_latest_user_index(messages: list[AgentMessage]) -> int | None:
    """返回最新 user 消息下标。

    Args:
        messages: 候选消息列表。

    Returns:
        int | None: 若存在 user 消息则返回其最新下标。
    """

    for idx in range(len(messages) - 1, -1, -1):
        if messages[idx].role == "user":
            return idx
    return None


def _dedup_preserve_order(items: list[str]) -> list[str]:
    """在保持顺序的前提下去重。

    Args:
        items: 原始列表。

    Returns:
        list[str]: 去重后的列表。
    """

    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output
