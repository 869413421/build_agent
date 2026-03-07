"""Context Engineering 的 ModelRuntime Hook 集成。"""

from __future__ import annotations

from typing import Any

from agent_forge.components.context_engineering.application.runtime import ContextEngineeringRuntime
from agent_forge.components.context_engineering.domain import CitationItem, ContextBudget
from agent_forge.components.model_runtime.domain import ModelRequest, ModelResponse, ModelRuntimeHooks, ModelStreamEvent


class ContextEngineeringHook(ModelRuntimeHooks):
    """在模型请求发出前执行上下文编排与裁剪。"""

    def __init__(
        self,
        runtime: ContextEngineeringRuntime,
        *,
        budget: ContextBudget,
        citations: list[CitationItem] | None = None,
        tools: list[dict[str, Any]] | None = None,
        developer_prompt: str | None = None,
    ) -> None:
        """初始化上下文编排 Hook。

        Args:
            runtime: Context Engineering 运行时。
            budget: 当前生效的上下文预算。
            citations: 可选默认引用列表。
            tools: 可选默认工具列表。
            developer_prompt: 可选注入的 developer 提示词。

        Returns:
            None.
        """

        self._runtime = runtime
        self._budget = budget
        self._citations = [item.model_copy(deep=True) for item in (citations or [])]
        self._tools = [dict(item) for item in (tools or [])]
        self._developer_prompt = developer_prompt

    def before_request(self, request: ModelRequest) -> ModelRequest:
        """在适配器调用前构建并裁剪模型上下文。

        Args:
            request: 原始模型请求。

        Returns:
            ModelRequest: 注入裁剪结果后的请求。
        """

        # 1. 从 request 透传参数中解析动态输入源。
        extra = request.extra_kwargs()
        citations = self._resolve_citations(extra.get("citations"))
        tools = self._resolve_tools(extra.get("tools"), request.tools)

        # 2. 按确定性预算策略构建 ContextBundle。
        bundle = self._runtime.build_bundle(
            system_prompt=request.system_prompt,
            messages=request.messages,
            tools=tools,
            citations=citations,
            budget=self._budget,
            developer_prompt=self._developer_prompt,
        )

        # 3. 返回拷贝后的请求，并附带预算报告供观测使用。
        updated = request.model_copy(deep=True)
        updated.messages = bundle.messages
        updated.system_prompt = bundle.system_prompt
        updated.tools = bundle.tools
        setattr(updated, "context_budget_report", bundle.budget_report.model_dump())
        return updated

    def on_stream_event(self, event: ModelStreamEvent) -> ModelStreamEvent:
        """透传流式事件，不做改写。

        Args:
            event: 流式事件。

        Returns:
            ModelStreamEvent: 原样返回事件。
        """

        return event

    def after_response(self, response: ModelResponse) -> ModelResponse:
        """透传最终响应，不做改写。

        Args:
            response: 模型响应。

        Returns:
            ModelResponse: 原样返回响应。
        """

        return response

    def _resolve_citations(self, raw: Any) -> list[CitationItem]:
        """从 Hook 默认值或 request 参数中解析 citations。

        Args:
            raw: 可选原始 citations 载荷。

        Returns:
            list[CitationItem]: 解析后的引用列表。
        """

        if raw is None:
            return [item.model_copy(deep=True) for item in self._citations]
        if not isinstance(raw, list):
            return []
        output: list[CitationItem] = []
        for item in raw:
            if isinstance(item, CitationItem):
                output.append(item.model_copy(deep=True))
                continue
            if isinstance(item, dict):
                output.append(CitationItem(**item))
        return output

    def _resolve_tools(self, raw: Any, request_tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        """从 Hook 默认值或 request 参数中解析 tools。

        Args:
            raw: 可选原始 tools 载荷。
            request_tools: ModelRequest 上已经存在的 tools。

        Returns:
            list[dict[str, Any]]: 解析后的工具列表。
        """

        if raw is None:
            if request_tools is not None:
                return [dict(item) for item in request_tools]
            return [dict(item) for item in self._tools]
        if not isinstance(raw, list):
            return []
        output: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, dict):
                output.append(dict(item))
        return output
