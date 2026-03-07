"""Context Engineering 运行时。"""

from __future__ import annotations

from typing import Any

from agent_forge.components.context_engineering.application.policies import ConservativeTrimmingPolicy
from agent_forge.components.context_engineering.domain import CitationItem, ContextBudget, ContextBundle
from agent_forge.components.context_engineering.infrastructure import CharTokenEstimator, build_citation_message
from agent_forge.components.protocol import AgentMessage


class ContextEngineeringRuntime:
    """基于确定性预算策略生成 ContextBundle。"""

    def __init__(
        self,
        *,
        estimator: CharTokenEstimator | None = None,
        trimming_policy: ConservativeTrimmingPolicy | None = None,
    ) -> None:
        """初始化 Context Engineering 运行时。

        Args:
            estimator: 可选 Token 估算器覆盖实现。
            trimming_policy: 可选裁剪策略覆盖实现。

        Returns:
            None.
        """

        self._estimator = estimator or CharTokenEstimator()
        self._trimming_policy = trimming_policy or ConservativeTrimmingPolicy()

    def build_bundle(
        self,
        *,
        system_prompt: str | None,
        messages: list[AgentMessage],
        tools: list[dict[str, Any]] | None = None,
        citations: list[CitationItem] | None = None,
        budget: ContextBudget | None = None,
        developer_prompt: str | None = None,
    ) -> ContextBundle:
        """构建标准化的上下文产物。

        Args:
            system_prompt: 可选 system 提示词。
            messages: 原始消息列表。
            tools: 可选工具 schema 列表。
            citations: 可选引用列表。
            budget: 可选预算配置。
            developer_prompt: 可选注入 developer 提示词。

        Returns:
            ContextBundle: 含预算报告的裁剪结果。
        """

        # 1. 规范化输入并深拷贝，避免污染调用方对象。
        active_budget = budget or ContextBudget()
        normalized_messages = [item.model_copy(deep=True) for item in messages]
        normalized_tools = [dict(item) for item in (tools or [])]
        normalized_citations = [item.model_copy(deep=True) for item in (citations or [])]

        # 2. 将 developer_prompt 作为高优先级消息注入。
        if developer_prompt:
            normalized_messages.insert(
                0,
                AgentMessage(role="developer", content=developer_prompt),
            )

        # 3. 交给策略层执行裁剪，并组装最终 ContextBundle。
        kept_messages, kept_tools, kept_citations, report = self._trimming_policy.trim(
            system_prompt=system_prompt,
            messages=normalized_messages,
            tools=normalized_tools,
            citations=normalized_citations,
            budget=active_budget,
            estimator=self._estimator,
        )
        if kept_citations:
            kept_messages.append(build_citation_message(kept_citations))
            report = report.model_copy(update={"kept_messages": report.kept_messages + 1})

        return ContextBundle(
            system_prompt=system_prompt,
            messages=kept_messages,
            tools=kept_tools,
            citations=kept_citations,
            budget_report=report,
        )
