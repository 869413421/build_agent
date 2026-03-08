"""Safety 与 ToolRuntime 的桥接 hook。"""

from __future__ import annotations

from typing import Callable

from agent_forge.components.protocol import ToolCall, ToolResult
from agent_forge.components.safety.application.runtime import SafetyRuntime
from agent_forge.components.safety.domain import SafetyCheckRequest
from agent_forge.components.tool_runtime.application.hooks_dispatcher import get_current_hook_context
from agent_forge.components.tool_runtime import ToolRuntimeError, ToolRuntimeEvent
from agent_forge.components.tool_runtime.domain import ToolSpec


class SafetyToolRuntimeHook:
    """把工具前置审查接入 ToolRuntime before_execute。"""

    def __init__(
        self,
        safety_runtime: SafetyRuntime,
        *,
        spec_resolver: Callable[[str], ToolSpec] | None = None,
        capability_resolver: Callable[[str], set[str]] | None = None,
    ) -> None:
        """初始化 hook。

        Args:
            safety_runtime: Safety 运行时。
            spec_resolver: 工具规格解析器。
            capability_resolver: 主体到能力集合的解析器。
        """

        self._safety_runtime = safety_runtime
        self._spec_resolver = spec_resolver
        self._capability_resolver = capability_resolver or (lambda _principal: set())

    def before_execute(self, tool_call: ToolCall) -> ToolCall:
        """在真实执行前做安全审查。

        Args:
            tool_call: 原始工具调用。

        Returns:
            ToolCall: 原样返回的调用对象。

        Raises:
            ToolRuntimeError: 安全层拒绝时抛出统一工具运行时错误。
        """

        # 1. 收集上下文：在 hook 里补齐 ToolSpec 与 capability，避免 reviewer 直接耦合 ToolRuntime 内部对象。
        spec = self._resolve_spec(tool_call.tool_name)
        hook_context = get_current_hook_context()
        runtime_capabilities = hook_context.get("capabilities")
        if runtime_capabilities is None:
            capabilities = sorted(self._capability_resolver(tool_call.principal))
        else:
            capabilities = sorted(set(runtime_capabilities))
        # 2. 走统一 runtime：工具审查和输入/输出审查共用同一 SafetyDecision 契约。
        decision = self._safety_runtime.check_tool_call(
            SafetyCheckRequest(
                stage="tool",
                tool_call=tool_call,
                context={
                    "tool_spec": spec.model_dump(),
                    "capabilities": capabilities,
                },
            )
        )
        # 3. 拒绝即抛错：让 ToolRuntime 继续走既有 on_error / record / observability 语义。
        if not decision.allowed:
            raise ToolRuntimeError(
                error_code="TOOL_SAFETY_DENIED",
                message=decision.reason or "工具调用被安全策略拦截",
                retryable=False,
            )
        return tool_call

    def on_event(self, event: ToolRuntimeEvent) -> ToolRuntimeEvent | None:
        """透传 ToolRuntime 事件。

        Args:
            event: 原始运行时事件。

        Returns:
            ToolRuntimeEvent | None: 原样事件。
        """

        return event

    def after_execute(self, result: ToolResult) -> ToolResult:
        """透传执行结果。

        Args:
            result: 工具执行结果。

        Returns:
            ToolResult: 原样结果。
        """

        return result

    def on_error(self, error: ToolRuntimeError, tool_call: ToolCall) -> ToolRuntimeError:
        """透传错误对象。

        Args:
            error: 原始错误。
            tool_call: 对应工具调用。

        Returns:
            ToolRuntimeError: 原样错误。
        """

        _ = tool_call
        return error

    def _resolve_spec(self, tool_name: str) -> ToolSpec:
        """解析工具规格，失败时返回最小降级规格。

        Args:
            tool_name: 工具名称。

        Returns:
            ToolSpec: 真实规格或降级规格。
        """

        if self._spec_resolver is None:
            return ToolSpec(name=tool_name)
        try:
            return self._spec_resolver(tool_name)
        except Exception:
            return ToolSpec(name=tool_name)
