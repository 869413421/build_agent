"""面向用户的 Agent 门面，支持开箱即用与继承扩展。"""

from __future__ import annotations

import asyncio
from typing import Any

from agent_forge.runtime.runtime import AgentRuntime, build_default_agent_runtime
from agent_forge.runtime.schemas import AgentConfig, AgentResult, AgentRunRequest


class Agent:
    """用户级 Agent 入口。

    设计边界：
    1. 默认 `Agent()` 必须零配置可用。
    2. 子类可以通过受保护方法覆写局部行为，而不需要复制整条主流程。
    3. 真正的编排执行交给 `AgentRuntime`，`Agent` 只负责门面与扩展点。
    """

    def __init__(self, *, config: AgentConfig | None = None, runtime: AgentRuntime | None = None) -> None:
        """创建 Agent 实例。"""

        self.config = config or AgentConfig()
        self._runtime_override = runtime
        self.runtime = self._build_runtime()

    async def arun(self, task_input: str, **options: Any) -> AgentResult:
        """异步执行一次 Agent 主流程。"""

        request = self._build_request(task_input, **options)
        try:
            # 1. 在正式运行前，允许子类补充上下文、能力或元数据。
            request = self._before_run(request)
            # 2. 统一把执行委托给 AgentRuntime，避免门面层重复编排逻辑。
            result = await self.runtime.arun(request)
            # 3. 在结果返回前，允许子类包装输出或补充业务字段。
            return self._after_run(request, result)
        except Exception as exc:  # noqa: BLE001
            return self._on_error(request, exc)

    def run(self, task_input: str, **options: Any) -> AgentResult:
        """同步包装。

        设计约束：
        1. 同步入口只作为异步主链路的轻包装。
        2. 如果当前已经位于事件循环中，调用方必须改用 `await agent.arun(...)`。
        """

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(task_input, **options))
        raise RuntimeError("检测到已有运行中的事件循环，请改用 `await Agent.arun(...)`。")

    def _build_runtime(self) -> AgentRuntime:
        """构造内部运行时。

        子类可以覆写这里，替换默认的 `AgentRuntime` 装配方式。
        """

        if self._runtime_override is not None:
            return self._runtime_override
        return build_default_agent_runtime(config=self.config)

    def _build_request(self, task_input: str, **options: Any) -> AgentRunRequest:
        """把用户输入规范化为 `AgentRunRequest`。"""

        # 1. 先集中收口扩展点，避免构造请求对象后再做零散修改。
        capabilities = self._get_capabilities(task_input, **options)
        context = self._get_context(task_input, **options)
        # 2. 统一映射可选字段，保证 AgentRuntime 看到的请求结构稳定。
        return AgentRunRequest(
            task_input=task_input,
            session_id=options.get("session_id"),
            trace_id=options.get("trace_id"),
            principal=options.get("principal"),
            capabilities=capabilities,
            context=context,
            tenant_id=options.get("tenant_id"),
            user_id=options.get("user_id"),
            evaluate=options.get("evaluate"),
            metadata=dict(options.get("metadata") or {}),
        )

    def _before_run(self, request: AgentRunRequest) -> AgentRunRequest:
        """运行前钩子。"""

        return request

    def _after_run(self, request: AgentRunRequest, result: AgentResult) -> AgentResult:
        """运行后钩子。"""

        _ = request
        return result

    def _on_error(self, request: AgentRunRequest, error: Exception) -> AgentResult:
        """把未捕获异常收口成稳定的 `AgentResult`。"""

        from agent_forge.components.protocol import ErrorInfo

        return AgentResult(
            status="failed",
            summary=f"Agent 运行失败：{error}",
            output={"message": str(error)},
            session_id=request.session_id or "unknown_session",
            trace_id=request.trace_id or "unknown_trace",
            error=ErrorInfo(error_code="AGENT_RUNTIME_EXCEPTION", error_message=str(error), retryable=False),
            metadata={"principal": request.principal or self.config.default_principal},
        )

    def _get_capabilities(self, task_input: str, **options: Any) -> set[str] | None:
        """解析本次运行的能力集合。"""

        _ = task_input
        capabilities = options.get("capabilities")
        if capabilities is None:
            return None
        return set(capabilities)

    def _get_context(self, task_input: str, **options: Any) -> dict[str, Any]:
        """解析本次运行的上下文。"""

        _ = task_input
        return dict(options.get("context") or {})
