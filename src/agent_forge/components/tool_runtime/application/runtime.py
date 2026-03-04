"""Tool Runtime 门面。"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from agent_forge.components.protocol import ToolCall, ToolResult
from agent_forge.components.tool_runtime.application.chain_runner import ToolChainRunner, ToolChainResult
from agent_forge.components.tool_runtime.application.executor import ToolExecutor, ToolHandler
from agent_forge.components.tool_runtime.application.hooks_dispatcher import HookDispatcher
from agent_forge.components.tool_runtime.application.utils import mask_sensitive_fields
from agent_forge.components.tool_runtime.domain.schemas import (
    ToolChainStep,
    ToolExecutionRecord,
    ToolRuntimeHooks,
    ToolRuntimeError,
    ToolSpec,
)
from agent_forge.support.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_CACHE_MAXSIZE = 1024
_DEFAULT_RECORDS_MAXSIZE = 10000


class ToolRuntime:
    """统一工具运行时门面。"""

    def __init__(
        self,
        default_timeout_ms: int = 2000,
        max_retries: int = 0,
        hooks: list[ToolRuntimeHooks] | None = None,
        cache_maxsize: int = _DEFAULT_CACHE_MAXSIZE,
        records_maxsize: int = _DEFAULT_RECORDS_MAXSIZE,
    ) -> None:
        """初始化 ToolRuntime 门面。

        Args:
            default_timeout_ms: 默认工具超时（毫秒）。
            max_retries: 可重试错误的最大重试次数。
            hooks: 可选 hooks 列表。
            cache_maxsize: 幂等缓存最大条数（LRU）。
            records_maxsize: 执行记录最大保留条数。
        """
        # 1. 状态容器：ToolRuntime 负责持有注册表、幂等缓存与执行记录。
        self.default_timeout_ms = default_timeout_ms
        self.max_retries = max_retries
        self._cache_maxsize = cache_maxsize
        self._records_maxsize = records_maxsize
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, ToolHandler] = {}
        # LRU 缓存：OrderedDict 实现 O(1) 淘汰最久未使用条目，防止无界增长（H-4）。
        self._idempotency_cache: OrderedDict[str, ToolResult] = OrderedDict()
        self._records: list[ToolExecutionRecord] = []

        # 2. 组装协作对象：把 hooks、执行、链式编排拆为独立服务，避免门面膨胀。
        self._hook_dispatcher = HookDispatcher(hooks=hooks)
        self._executor = ToolExecutor(
            default_timeout_ms=self.default_timeout_ms,
            max_retries=self.max_retries,
            idempotency_cache=self._idempotency_cache,
            resolve_spec=self._resolve_tool_spec,
            resolve_handler=self._resolve_tool_handler,
            persist_result=self._persist_result,
            hook_dispatcher=self._hook_dispatcher,
        )
        self._chain_runner = ToolChainRunner(
            hook_dispatcher=self._hook_dispatcher,
            execute_sync=self._executor.execute,
            execute_async=self._executor.execute_async,
        )

    def register_tool(self, spec: ToolSpec, handler: ToolHandler) -> None:
        """注册工具。

        Args:
            spec: 工具规格定义。
            handler: 工具处理函数（同步或异步）。

        Raises:
            ValueError: 工具名重复注册时抛出。
        """

        if spec.name in self._specs:
            raise ValueError(f"工具已注册: {spec.name}")
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler

    def register_hook(self, hook: ToolRuntimeHooks) -> None:
        """注册运行时 hook。

        Args:
            hook: 需要注册的 hook 实现。
        """

        self._hook_dispatcher.add_hook(hook)

    def get_records(self) -> list[ToolExecutionRecord]:
        """返回执行记录快照。

        Returns:
            list[ToolExecutionRecord]: 当前记录副本。
        """

        return list(self._records)

    def execute(
        self,
        tool_call: ToolCall,
        principal: str | None = None,
        capabilities: set[str] | None = None,
    ) -> ToolResult:
        """同步执行一次工具调用。

        Args:
            tool_call: 工具调用对象。
            principal: 可选覆盖执行主体。
            capabilities: 可选能力集合。

        Returns:
            ToolResult: 结构化执行结果。
        """

        return self._executor.execute(tool_call=tool_call, principal=principal, capabilities=capabilities)

    async def execute_async(
        self,
        tool_call: ToolCall,
        principal: str | None = None,
        capabilities: set[str] | None = None,
    ) -> ToolResult:
        """异步执行一次工具调用。

        Args:
            tool_call: 工具调用对象。
            principal: 可选覆盖执行主体。
            capabilities: 可选能力集合。

        Returns:
            ToolResult: 结构化执行结果。
        """

        return await self._executor.execute_async(tool_call=tool_call, principal=principal, capabilities=capabilities)

    async def execute_many_async(
        self,
        tool_calls: list[ToolCall],
        principal: str | None = None,
        capabilities: set[str] | None = None,
        max_concurrency: int = 8,
    ) -> list[ToolResult]:
        """异步批量执行工具调用（输入顺序 -> 输出顺序）。

        Args:
            tool_calls: 待执行调用列表。
            principal: 可选覆盖执行主体。
            capabilities: 可选能力集合。
            max_concurrency: 最大并发度。

        Returns:
            list[ToolResult]: 与输入顺序一致的结果列表。
        """

        # 1. 门面代理：批量执行策略集中在 executor，门面只暴露稳定接口。
        return await self._executor.execute_many_async(
            tool_calls=tool_calls,
            principal=principal,
            capabilities=capabilities,
            max_concurrency=max_concurrency,
        )

    def run_chain(
        self,
        chain_id: str,
        steps: list[ToolChainStep],
        principal: str | None = None,
        capabilities: set[str] | None = None,
    ) -> ToolChainResult:
        """同步执行工具链。

        Args:
            chain_id: 链路ID。
            steps: 链路步骤列表。
            principal: 可选默认执行主体。
            capabilities: 可选默认能力集合。

        Returns:
            ToolChainResult: 链路执行结果。
        """

        return self._chain_runner.run(chain_id=chain_id, steps=steps, principal=principal, capabilities=capabilities)

    async def arun_chain(
        self,
        chain_id: str,
        steps: list[ToolChainStep],
        principal: str | None = None,
        capabilities: set[str] | None = None,
    ) -> ToolChainResult:
        """异步执行工具链。

        Args:
            chain_id: 链路ID。
            steps: 链路步骤列表。
            principal: 可选默认执行主体。
            capabilities: 可选默认能力集合。

        Returns:
            ToolChainResult: 链路执行结果。
        """

        return await self._chain_runner.arun(
            chain_id=chain_id,
            steps=steps,
            principal=principal,
            capabilities=capabilities,
        )

    def _resolve_tool_spec(self, tool_name: str) -> ToolSpec:
        """按工具名解析 ToolSpec。

        Args:
            tool_name: 工具名称。

        Returns:
            ToolSpec: 工具规格。

        Raises:
            ToolRuntimeError: 工具未注册时抛出。
        """
        if tool_name not in self._specs:
            raise ToolRuntimeError(error_code="TOOL_NOT_FOUND", message=f"未注册工具: {tool_name}")
        return self._specs[tool_name]

    def _resolve_tool_handler(self, tool_name: str) -> ToolHandler:
        """按工具名解析 handler。

        Args:
            tool_name: 工具名称。

        Returns:
            ToolHandler: 工具处理器。

        Raises:
            ToolRuntimeError: 处理器未注册时抛出。
        """
        if tool_name not in self._handlers:
            raise ToolRuntimeError(error_code="TOOL_NOT_FOUND", message=f"未注册工具处理器: {tool_name}")
        return self._handlers[tool_name]

    def _persist_result(self, spec: ToolSpec, tool_call: ToolCall, principal: str, result: ToolResult) -> None:
        """持久化执行结果到幂等缓存与执行记录。

        Args:
            spec: 工具规格（用于脱敏字段定义）。
            tool_call: 原始工具调用。
            principal: 执行主体。
            result: 执行结果。
        """
        # 幂等缓存写入：超过上限时淘汰最久未使用的条目（LRU）。
        self._idempotency_cache[tool_call.tool_call_id] = result
        self._idempotency_cache.move_to_end(tool_call.tool_call_id)
        if len(self._idempotency_cache) > self._cache_maxsize:
            self._idempotency_cache.popitem(last=False)

        record = ToolExecutionRecord(
            tool_call_id=tool_call.tool_call_id,
            tool_name=tool_call.tool_name,
            principal=principal,
            status=result.status,
            args_masked=mask_sensitive_fields(tool_call.args, spec.sensitive_fields),
            output=result.output,
            error=result.error,
            latency_ms=result.latency_ms,
        )
        self._records.append(record)
        # 执行记录滚动截断：超过上限时丢弃最旧的条目，防止无界增长（H-4）。
        if len(self._records) > self._records_maxsize:
            self._records = self._records[-self._records_maxsize :]
        logger.info("tool executed: %s status=%s call_id=%s", tool_call.tool_name, result.status, tool_call.tool_call_id)
