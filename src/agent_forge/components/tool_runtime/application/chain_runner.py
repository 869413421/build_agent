"""Tool Runtime 链式编排服务。"""

from __future__ import annotations

from typing import Any, Callable, Coroutine, TypedDict

from agent_forge.components.protocol import ToolCall, ToolResult
from agent_forge.components.tool_runtime.application.hooks_dispatcher import HookDispatcher
from agent_forge.components.tool_runtime.domain.schemas import ToolChainStep, ToolRuntimeError, ToolRuntimeEvent

ExecuteSync = Callable[[ToolCall, str | None, set[str] | None], ToolResult]
ExecuteAsync = Callable[[ToolCall, str | None, set[str] | None], Coroutine[Any, Any, ToolResult]]


class ToolChainResult(TypedDict):
    """工具链执行结果。"""

    chain_id: str
    status: str
    results: list[ToolResult]
    outputs: dict[str, dict[str, Any]]


class ToolChainRunner:
    """负责工具链步骤编排与依赖绑定。"""

    def __init__(self, *, hook_dispatcher: HookDispatcher, execute_sync: ExecuteSync, execute_async: ExecuteAsync) -> None:
        """初始化链式编排器。

        Args:
            hook_dispatcher: hooks 分发器，用于链路级事件发射。
            execute_sync: 同步单步执行函数。
            execute_async: 异步单步执行函数。
        """
        self.hooks = hook_dispatcher
        self.execute_sync = execute_sync
        self.execute_async_fn = execute_async

    def run(
        self,
        chain_id: str,
        steps: list[ToolChainStep],
        principal: str | None = None,
        capabilities: set[str] | None = None,
    ) -> ToolChainResult:
        """同步执行工具链。

        设计边界：
        - 仅负责步骤编排与依赖绑定，不承担单步执行语义（交给 executor）。

        Args:
            chain_id: 链路ID，用于事件关联和回放。
            steps: 工具链步骤列表。
            principal: 可选默认执行主体。
            capabilities: 可选默认能力集合。

        Returns:
            ToolChainResult: 链路执行结果（状态、步骤结果与输出聚合）。
        """
        outputs: dict[str, dict[str, Any]] = {}
        results: list[ToolResult] = []
        status = "ok"
        for index, step in enumerate(steps):
            # 1. 进入步骤：发 start 事件，便于链路级追踪。
            self.hooks.emit_event(
                ToolRuntimeEvent(
                    event_type="chain_step_start",
                    chain_id=chain_id,
                    step_id=step.step_id,
                    payload={"index": index, "tool_name": step.tool_name},
                )
            )
            # 2. 构建调用：把静态 args 和 input_bindings 合并成最终 ToolCall。
            call = self._build_call(chain_id, step, outputs, principal)
            result = self.execute_sync(call, step.principal or principal, step.capabilities or capabilities)
            results.append(result)
            outputs[step.step_id] = result.output
            # 3. 结束步骤：记录 end 事件并按 stop_on_error 决定是否短路。
            self.hooks.emit_event(
                ToolRuntimeEvent(
                    event_type="chain_step_end",
                    chain_id=chain_id,
                    step_id=step.step_id,
                    tool_call_id=call.tool_call_id,
                    tool_name=call.tool_name,
                    latency_ms=result.latency_ms,
                    payload={"status": result.status},
                    error=result.error,
                )
            )
            if result.status == "error":
                status = "error"
                if step.stop_on_error:
                    break
        return {"chain_id": chain_id, "status": status, "results": results, "outputs": outputs}

    async def arun(
        self,
        chain_id: str,
        steps: list[ToolChainStep],
        principal: str | None = None,
        capabilities: set[str] | None = None,
    ) -> ToolChainResult:
        """异步执行工具链（语义与同步 run 一致）。

        Args:
            chain_id: 链路ID，用于事件关联和回放。
            steps: 工具链步骤列表。
            principal: 可选默认执行主体。
            capabilities: 可选默认能力集合。

        Returns:
            ToolChainResult: 链路执行结果（状态、步骤结果与输出聚合）。
        """
        outputs: dict[str, dict[str, Any]] = {}
        results: list[ToolResult] = []
        status = "ok"
        for index, step in enumerate(steps):
            # 1. 进入步骤：发 start 事件。
            self.hooks.emit_event(
                ToolRuntimeEvent(
                    event_type="chain_step_start",
                    chain_id=chain_id,
                    step_id=step.step_id,
                    payload={"index": index, "tool_name": step.tool_name},
                )
            )
            # 2. 构建调用并异步执行单步。
            call = self._build_call(chain_id, step, outputs, principal)
            result = await self.execute_async_fn(call, step.principal or principal, step.capabilities or capabilities)
            results.append(result)
            outputs[step.step_id] = result.output
            # 3. 发 end 事件并处理失败短路。
            self.hooks.emit_event(
                ToolRuntimeEvent(
                    event_type="chain_step_end",
                    chain_id=chain_id,
                    step_id=step.step_id,
                    tool_call_id=call.tool_call_id,
                    tool_name=call.tool_name,
                    latency_ms=result.latency_ms,
                    payload={"status": result.status},
                    error=result.error,
                )
            )
            if result.status == "error":
                status = "error"
                if step.stop_on_error:
                    break
        return {"chain_id": chain_id, "status": status, "results": results, "outputs": outputs}

    def _build_call(
        self,
        chain_id: str,
        step: ToolChainStep,
        outputs: dict[str, dict[str, Any]],
        principal: str | None,
    ) -> ToolCall:
        """构造链路步骤对应的 ToolCall。

        Args:
            chain_id: 链路ID。
            step: 当前步骤定义。
            outputs: 已完成步骤输出字典。
            principal: 默认执行主体。

        Returns:
            ToolCall: 最终可执行的工具调用对象。
        """
        args = dict(step.args)
        for arg_name, binding in step.input_bindings.items():
            args[arg_name] = _resolve_binding(binding, outputs)
        return ToolCall(
            tool_call_id=step.tool_call_id or f"{chain_id}:{step.step_id}",
            tool_name=step.tool_name,
            args=args,
            principal=step.principal or principal or "chain",
        )


def _resolve_binding(binding: str, outputs: dict[str, dict[str, Any]]) -> Any:
    """解析 `step.path` 形式的输入绑定。

    Args:
        binding: 绑定表达式，格式如 `step_id.field`。
        outputs: 历史步骤输出集合。

    Returns:
        Any: 绑定路径对应的值。

    Raises:
        ToolRuntimeError: 绑定表达式非法或路径不存在时抛出。
    """
    parts = binding.split(".")
    if len(parts) < 2:
        raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"非法 input_binding: {binding}")
    step_id, keys = parts[0], parts[1:]
    if step_id not in outputs:
        raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"绑定来源步骤不存在: {step_id}")
    value: Any = outputs[step_id]
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"绑定路径不存在: {binding}")
        value = value[key]
    return value
