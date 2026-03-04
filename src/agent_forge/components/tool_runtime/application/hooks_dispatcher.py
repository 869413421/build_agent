"""Tool Runtime hooks 分发器。"""

from __future__ import annotations

from agent_forge.components.protocol import ToolCall, ToolResult
from agent_forge.components.tool_runtime.domain.schemas import (
    NoopToolRuntimeHooks,
    ToolRuntimeError,
    ToolRuntimeEvent,
    ToolRuntimeHooks,
)


class HookDispatcher:
    """统一分发 hooks，隔离运行时与钩子细节。"""

    def __init__(self, hooks: list[ToolRuntimeHooks] | None = None) -> None:
        """初始化 hooks 分发器。

        Args:
            hooks: 可选 hooks 列表；为空时走 Noop hooks。
        """
        self._hooks = hooks or []
        self._noop = NoopToolRuntimeHooks()

    def add_hook(self, hook: ToolRuntimeHooks) -> None:
        """注册一个新的 hook。

        Args:
            hook: 需要纳入分发链的 hook 实现。
        """
        self._hooks.append(hook)

    def before_execute(self, tool_call: ToolCall) -> ToolCall:
        """分发 before_execute。

        Args:
            tool_call: 待执行的工具调用。

        Returns:
            ToolCall: 经过 hooks 处理后的调用对象。
        """
        call = tool_call
        if not self._hooks:
            return self._noop.before_execute(call)
        for hook in self._hooks:
            call = hook.before_execute(call)
        return call

    def after_execute(self, result: ToolResult) -> ToolResult:
        """分发 after_execute。

        Args:
            result: 原始执行结果。

        Returns:
            ToolResult: 经过 hooks 处理后的结果。
        """
        res = result
        if not self._hooks:
            return self._noop.after_execute(res)
        for hook in self._hooks:
            res = hook.after_execute(res)
        return res

    def on_error(self, error: ToolRuntimeError, tool_call: ToolCall) -> ToolRuntimeError:
        """分发 on_error。

        Args:
            error: 运行时错误对象。
            tool_call: 对应的工具调用。

        Returns:
            ToolRuntimeError: 经 hooks 处理后的错误对象。
        """
        err = error
        if not self._hooks:
            return self._noop.on_error(err, tool_call)
        for hook in self._hooks:
            err = hook.on_error(err, tool_call)
        return err

    def emit_event(self, event: ToolRuntimeEvent) -> None:
        """分发运行时事件。

        Args:
            event: 需要广播的运行时事件。
        """
        if not self._hooks:
            self._noop.on_event(event)
            return
        for hook in self._hooks:
            hook.on_event(event)
