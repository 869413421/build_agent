"""Tool Runtime -> Observability hooks。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_forge.components.protocol import ToolCall, ToolResult
from agent_forge.components.tool_runtime import ToolRuntimeError, ToolRuntimeEvent, ToolRuntimeHooks

if TYPE_CHECKING:
    from agent_forge.components.observability.application.runtime import ObservabilityRuntime


class ToolRuntimeObservabilityHook(ToolRuntimeHooks):
    """把 ToolRuntime 事件桥接到 ObservabilityRuntime。"""

    def __init__(self, runtime: "ObservabilityRuntime") -> None:
        """初始化 hook。

        Args:
            runtime: Observability 运行时实例。
        """

        self.runtime = runtime
        self._calls: dict[str, ToolCall] = {}
        self._contexts: dict[str, tuple[str, str]] = {}

    def before_execute(self, tool_call: ToolCall) -> ToolCall:
        """执行前记录调用参数。

        Args:
            tool_call: 工具调用对象。

        Returns:
            ToolCall: 原始调用对象（不改写）。
        """

        self._calls[tool_call.tool_call_id] = tool_call
        self._contexts[tool_call.tool_call_id] = self.runtime.get_current_context()
        return tool_call

    def on_event(self, event: ToolRuntimeEvent) -> ToolRuntimeEvent | None:
        """接收 ToolRuntime 事件并透传到观测运行时。

        Args:
            event: ToolRuntime 事件对象。

        Returns:
            ToolRuntimeEvent | None: 原样返回事件。
        """

        context = self._contexts.get(event.tool_call_id, self.runtime.get_current_context())
        self.runtime.capture_tool_event(event, trace_id=context[0], run_id=context[1])
        return event

    def after_execute(self, result: ToolResult) -> ToolResult:
        """在工具执行收尾后录制回放数据。

        Args:
            result: 工具执行结果。

        Returns:
            ToolResult: 原始结果。
        """

        tool_call = self._calls.pop(result.tool_call_id, None)
        context = self._contexts.pop(result.tool_call_id, self.runtime.get_current_context())
        if tool_call is not None:
            self.runtime.capture_tool_result(tool_call=tool_call, result=result, trace_id=context[0], run_id=context[1])
        return result

    def on_error(self, error: ToolRuntimeError, tool_call: ToolCall) -> ToolRuntimeError:
        """错误路径保持透传。

        Args:
            error: ToolRuntime 错误对象。
            tool_call: 当前工具调用。

        Returns:
            ToolRuntimeError: 原始错误对象。
        """

        self._calls[tool_call.tool_call_id] = tool_call
        if tool_call.tool_call_id not in self._contexts:
            self._contexts[tool_call.tool_call_id] = self.runtime.get_current_context()
        return error
