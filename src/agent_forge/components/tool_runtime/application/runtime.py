"""Tool Runtime 应用层入口。"""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock

from agent_forge.components.protocol import ToolCall, ToolResult
from agent_forge.components.tool_runtime.application.chain_runner import ToolChainRunner, ToolChainResult
from agent_forge.components.tool_runtime.application.executor import ToolExecutor, ToolHandler
from agent_forge.components.tool_runtime.application.hooks_dispatcher import HookDispatcher
from agent_forge.components.tool_runtime.application.utils import mask_sensitive_fields
from agent_forge.components.tool_runtime.domain.schemas import (
    ToolChainStep,
    ToolExecutionRecord,
    ToolRuntimeError,
    ToolRuntimeHooks,
    ToolSpec,
)
from agent_forge.support.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_CACHE_MAXSIZE = 1024
_DEFAULT_RECORDS_MAXSIZE = 10000


class ToolRuntime:
    """负责工具注册、执行、幂等缓存和执行记录。"""

    def __init__(
        self,
        default_timeout_ms: int = 2000,
        max_retries: int = 0,
        hooks: list[ToolRuntimeHooks] | None = None,
        cache_maxsize: int = _DEFAULT_CACHE_MAXSIZE,
        records_maxsize: int = _DEFAULT_RECORDS_MAXSIZE,
    ) -> None:
        """初始化 ToolRuntime。

        设计边界：
        1. 运行时只管理工具执行，不负责能力注册中心语义。
        2. 幂等缓存和执行记录都属于共享状态，必须统一加锁保护。
        3. 具体执行交给 executor / chain runner，当前类只负责装配与状态管理。
        """

        self.default_timeout_ms = default_timeout_ms
        self.max_retries = max_retries
        self._cache_maxsize = cache_maxsize
        self._records_maxsize = records_maxsize
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, ToolHandler] = {}
        self._state_lock = Lock()
        self._idempotency_cache: OrderedDict[str, ToolResult] = OrderedDict()
        self._records: list[ToolExecutionRecord] = []

        self._hook_dispatcher = HookDispatcher(hooks=hooks)
        self._executor = ToolExecutor(
            default_timeout_ms=self.default_timeout_ms,
            max_retries=self.max_retries,
            resolve_cached_result=self._get_cached_result,
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
        """注册一条工具定义。"""

        if spec.name in self._specs:
            raise ValueError(f"工具已存在: {spec.name}")
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler

    def register_hook(self, hook: ToolRuntimeHooks) -> None:
        """注册运行时 hook。"""

        self._hook_dispatcher.add_hook(hook)

    def get_records(self) -> list[ToolExecutionRecord]:
        """返回执行记录快照。"""

        with self._state_lock:
            return list(self._records)

    def list_tool_specs(self) -> list[ToolSpec]:
        """列出当前已注册的工具规格。"""

        with self._state_lock:
            specs_snapshot = list(self._specs.values())
        return [item.model_copy(deep=True) for item in specs_snapshot]

    def get_tool_spec(self, tool_name: str) -> ToolSpec:
        """按名字读取工具规格。"""

        return self._resolve_tool_spec(tool_name)

    def execute(
        self,
        tool_call: ToolCall,
        principal: str | None = None,
        capabilities: set[str] | None = None,
    ) -> ToolResult:
        """同步执行单次工具调用。"""

        return self._executor.execute(tool_call=tool_call, principal=principal, capabilities=capabilities)

    async def execute_async(
        self,
        tool_call: ToolCall,
        principal: str | None = None,
        capabilities: set[str] | None = None,
    ) -> ToolResult:
        """异步执行单次工具调用。"""

        return await self._executor.execute_async(tool_call=tool_call, principal=principal, capabilities=capabilities)

    async def execute_many_async(
        self,
        tool_calls: list[ToolCall],
        principal: str | None = None,
        capabilities: set[str] | None = None,
        max_concurrency: int = 8,
    ) -> list[ToolResult]:
        """并发执行多次工具调用。"""

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
        """同步执行工具链。"""

        return self._chain_runner.run(chain_id=chain_id, steps=steps, principal=principal, capabilities=capabilities)

    async def arun_chain(
        self,
        chain_id: str,
        steps: list[ToolChainStep],
        principal: str | None = None,
        capabilities: set[str] | None = None,
    ) -> ToolChainResult:
        """异步执行工具链。"""

        return await self._chain_runner.arun(
            chain_id=chain_id,
            steps=steps,
            principal=principal,
            capabilities=capabilities,
        )

    def _get_cached_result(self, tool_call_id: str) -> ToolResult | None:
        """读取幂等缓存。"""

        # 1. 所有共享缓存读取都必须在锁内完成，避免并发读取和写入交错。
        # 2. 这里只返回快照引用，不在读取时改动 LRU 顺序，保持幂等语义简单稳定。
        with self._state_lock:
            return self._idempotency_cache.get(tool_call_id)

    def _resolve_tool_spec(self, tool_name: str) -> ToolSpec:
        """解析工具规格。"""

        if tool_name not in self._specs:
            raise ToolRuntimeError(error_code="TOOL_NOT_FOUND", message=f"未注册的工具: {tool_name}")
        return self._specs[tool_name]

    def _resolve_tool_handler(self, tool_name: str) -> ToolHandler:
        """解析工具处理函数。"""

        if tool_name not in self._handlers:
            raise ToolRuntimeError(error_code="TOOL_NOT_FOUND", message=f"未找到工具处理函数: {tool_name}")
        return self._handlers[tool_name]

    def _persist_result(self, spec: ToolSpec, tool_call: ToolCall, principal: str, result: ToolResult) -> None:
        """持久化一次工具执行结果。"""

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
        with self._state_lock:
            # 1. 更新幂等缓存，维持 LRU 顺序与上限裁剪。
            self._idempotency_cache[tool_call.tool_call_id] = result
            self._idempotency_cache.move_to_end(tool_call.tool_call_id)
            if len(self._idempotency_cache) > self._cache_maxsize:
                self._idempotency_cache.popitem(last=False)

            # 2. 追加执行记录，并按窗口上限裁剪历史。
            self._records.append(record)
            if len(self._records) > self._records_maxsize:
                self._records = self._records[-self._records_maxsize :]
        logger.info("tool executed: %s status=%s call_id=%s", tool_call.tool_name, result.status, tool_call.tool_call_id)
