"""Tool Runtime 执行服务。"""

from __future__ import annotations

import asyncio
import inspect
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from time import monotonic
from typing import Any, Awaitable, Callable

from agent_forge.components.protocol import ErrorInfo, ToolCall, ToolResult
from agent_forge.components.tool_runtime.application.hooks_dispatcher import HookDispatcher
from agent_forge.components.tool_runtime.domain.schemas import ToolRuntimeError, ToolRuntimeEvent, ToolSpec

ToolHandler = Callable[[dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any]]]
ResolveToolSpec = Callable[[str], ToolSpec]
ResolveToolHandler = Callable[[str], ToolHandler]
PersistResult = Callable[[ToolSpec, ToolCall, str, ToolResult], None]


class ToolExecutor:
    """负责工具调用执行与错误语义收口。"""

    def __init__(
        self,
        *,
        default_timeout_ms: int,
        max_retries: int,
        idempotency_cache: dict[str, ToolResult],
        resolve_spec: ResolveToolSpec,
        resolve_handler: ResolveToolHandler,
        persist_result: PersistResult,
        hook_dispatcher: HookDispatcher,
    ) -> None:
        """初始化执行服务。

        Args:
            default_timeout_ms: 默认超时时间（毫秒）。
            max_retries: 可重试错误最大重试次数。
            idempotency_cache: 幂等缓存容器。
            resolve_spec: 工具规格解析函数。
            resolve_handler: 工具处理器解析函数。
            persist_result: 结果持久化回调。
            hook_dispatcher: hooks 分发器。
        """
        self.default_timeout_ms = default_timeout_ms
        self.max_retries = max_retries
        self.idempotency_cache = idempotency_cache
        self.resolve_spec = resolve_spec
        self.resolve_handler = resolve_handler
        self.persist_result = persist_result
        self.hooks = hook_dispatcher

    def execute(
        self,
        tool_call: ToolCall,
        principal: str | None = None,
        capabilities: set[str] | None = None,
    ) -> ToolResult:
        """同步执行单个工具调用。

        设计意图：
        - 对外统一返回 `ToolResult`，不把内部异常传播给 Engine。
        - 把幂等、校验、重试、超时、hooks 事件收敛在同一条稳定流程里。
        Args:
            tool_call: 工具调用对象。
            principal: 可选覆盖执行主体。
            capabilities: 可选能力集合。

        Returns:
            ToolResult: 结构化执行结果。
        """
        started_at = monotonic()
        actor = principal or tool_call.principal

        # 1. before hook：允许上层在执行前重写参数（如审计字段补齐、参数裁剪）。
        call = self.hooks.before_execute(tool_call)

        # 2. 幂等命中：同一个 tool_call_id 永远返回首个结果，避免副作用重复执行。
        cached = self.idempotency_cache.get(call.tool_call_id)
        if cached is not None:
            self.hooks.emit_event(
                ToolRuntimeEvent(
                    event_type="cache_hit",
                    tool_call_id=call.tool_call_id,
                    tool_name=call.tool_name,
                    latency_ms=cached.latency_ms,
                    payload={"status": cached.status},
                )
            )
            return cached

        # 3. 前置门禁：工具存在性、权限、参数结构在调用 handler 前完成校验。
        #    resolve_spec 失败会抛出 ToolRuntimeError，被最外层统一收口。
        try:
            spec = self.resolve_spec(call.tool_name)
            self._check_capabilities(spec, capabilities or set())
            self._validate_args(spec, call.args)
        except ToolRuntimeError as exc:
            result = self._handle_terminal_error(exc, call, started_at, actor)
            return result

        # 4. 重试执行循环：on_error hook 只在循环内触发，不会被外层重复调用。
        result = self._run_sync_with_retry(spec, call, started_at, actor)
        return result

    async def execute_async(
        self,
        tool_call: ToolCall,
        principal: str | None = None,
        capabilities: set[str] | None = None,
    ) -> ToolResult:
        """异步执行单个工具调用。

        约束：
        - 行为语义与 `execute()` 保持一致（幂等、重试、错误映射、hooks 触发顺序）。
        - 只把执行模型换成 async/await，方便 I/O 工具并发。
        Args:
            tool_call: 工具调用对象。
            principal: 可选覆盖执行主体。
            capabilities: 可选能力集合。

        Returns:
            ToolResult: 结构化执行结果。
        """
        started_at = monotonic()
        actor = principal or tool_call.principal

        # 1. before hook：异步路径与同步路径保持同一参数治理入口。
        call = self.hooks.before_execute(tool_call)

        # 2. 幂等命中：直接返回缓存结果，不进入任何真实调用。
        cached = self.idempotency_cache.get(call.tool_call_id)
        if cached is not None:
            self.hooks.emit_event(
                ToolRuntimeEvent(
                    event_type="cache_hit",
                    tool_call_id=call.tool_call_id,
                    tool_name=call.tool_name,
                    latency_ms=cached.latency_ms,
                    payload={"status": cached.status},
                )
            )
            return cached

        # 3. 前置门禁：权限与参数校验先于执行，避免无效流量进入工具侧。
        try:
            spec = self.resolve_spec(call.tool_name)
            self._check_capabilities(spec, capabilities or set())
            self._validate_args(spec, call.args)
        except ToolRuntimeError as exc:
            result = self._handle_terminal_error(exc, call, started_at, actor)
            return result

        # 4. 重试执行循环：on_error hook 只在循环内触发，不会被外层重复调用。
        result = await self._run_async_with_retry(spec, call, started_at, actor)
        return result

    async def execute_many_async(
        self,
        tool_calls: list[ToolCall],
        principal: str | None = None,
        capabilities: set[str] | None = None,
        max_concurrency: int = 8,
    ) -> list[ToolResult]:
        """异步批量执行工具调用（保持输入顺序返回）。

        Args:
            tool_calls: 待执行调用列表。
            principal: 可选覆盖执行主体。
            capabilities: 可选能力集合。
            max_concurrency: 最大并发数。

        Returns:
            list[ToolResult]: 与输入顺序一致的执行结果列表。

        Raises:
            ValueError: max_concurrency 小于 1 时抛出。
        """

        if max_concurrency < 1:
            raise ValueError("max_concurrency 必须 >= 1")

        # 1. 并发控制：用信号量做背压，防止批量任务击穿外部依赖。
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _run_one(call: ToolCall) -> ToolResult:
            # 2. 单任务执行：复用单调用语义，避免批量路径出现语义分叉。
            async with semaphore:
                return await self.execute_async(
                    tool_call=call,
                    principal=principal,
                    capabilities=capabilities,
                )

        # 3. 顺序稳定：gather 按输入顺序返回，便于上游和原请求一一对应。
        return await asyncio.gather(*[_run_one(call) for call in tool_calls])

    # ------------------------------------------------------------------
    # 私有：重试循环核心（sync / async 各一份，仅执行调度不同）
    # ------------------------------------------------------------------

    def _run_sync_with_retry(
        self, spec: ToolSpec, call: ToolCall, started_at: float, actor: str
    ) -> ToolResult:
        """同步重试循环。

        Args:
            spec: 工具规格。
            call: 处理后的工具调用。
            started_at: 执行起始时间（monotonic）。
            actor: 执行主体。

        Returns:
            ToolResult: 成功结果或最终失败结果。
        """
        attempt = 0
        while True:
            self.hooks.emit_event(
                ToolRuntimeEvent(
                    event_type="before_execute",
                    tool_call_id=call.tool_call_id,
                    tool_name=call.tool_name,
                    attempt=attempt,
                )
            )
            try:
                output = self._run_with_timeout_sync(
                    handler=self.resolve_handler(call.tool_name),
                    args=call.args,
                    timeout_ms=spec.timeout_ms or self.default_timeout_ms,
                )
                return self._finalize_success(spec, call, actor, started_at, attempt, output)
            except ToolRuntimeError as exc:
                hooked, should_retry = self._handle_retry_error(exc, call, attempt)
                if should_retry:
                    attempt += 1
                    continue
                return self._finalize_error(spec, call, actor, started_at, attempt, hooked)

    async def _run_async_with_retry(
        self, spec: ToolSpec, call: ToolCall, started_at: float, actor: str
    ) -> ToolResult:
        """异步重试循环。

        Args:
            spec: 工具规格。
            call: 处理后的工具调用。
            started_at: 执行起始时间（monotonic）。
            actor: 执行主体。

        Returns:
            ToolResult: 成功结果或最终失败结果。
        """
        attempt = 0
        while True:
            self.hooks.emit_event(
                ToolRuntimeEvent(
                    event_type="before_execute",
                    tool_call_id=call.tool_call_id,
                    tool_name=call.tool_name,
                    attempt=attempt,
                )
            )
            try:
                output = await self._run_with_timeout_async(
                    handler=self.resolve_handler(call.tool_name),
                    args=call.args,
                    timeout_ms=spec.timeout_ms or self.default_timeout_ms,
                )
                return self._finalize_success(spec, call, actor, started_at, attempt, output)
            except ToolRuntimeError as exc:
                hooked, should_retry = self._handle_retry_error(exc, call, attempt)
                if should_retry:
                    attempt += 1
                    continue
                return self._finalize_error(spec, call, actor, started_at, attempt, hooked)

    def _handle_retry_error(
        self, exc: ToolRuntimeError, call: ToolCall, attempt: int
    ) -> tuple[ToolRuntimeError, bool]:
        """处理重试循环内的错误：触发 on_error hook 与 error 事件，返回 (hooked_error, should_retry)。

        Args:
            exc: 原始错误。
            call: 当前工具调用。
            attempt: 当前尝试次数。

        Returns:
            tuple[ToolRuntimeError, bool]:
                - 第1项为 hook 处理后的错误对象；
                - 第2项为是否继续重试。
        on_error hook 只在这里调用一次，彻底避免外层重复触发（CRITICAL-1 修复）。
        """
        hooked = self.hooks.on_error(exc, call)
        self.hooks.emit_event(
            ToolRuntimeEvent(
                event_type="error",
                tool_call_id=call.tool_call_id,
                tool_name=call.tool_name,
                attempt=attempt,
                error=ErrorInfo(
                    error_code=hooked.error_code,
                    error_message=hooked.message,
                    retryable=hooked.retryable,
                ),
            )
        )
        should_retry = hooked.retryable and attempt < self.max_retries
        return hooked, should_retry

    def _handle_terminal_error(
        self, exc: ToolRuntimeError, call: ToolCall, started_at: float, actor: str
    ) -> ToolResult:
        """处理前置门禁失败（resolve_spec/权限/参数校验）。

        Args:
            exc: 原始错误。
            call: 当前工具调用。
            started_at: 执行起始时间。
            actor: 执行主体。

        Returns:
            ToolResult: 结构化失败结果。
        """
        hooked = self.hooks.on_error(exc, call)
        self.hooks.emit_event(
            ToolRuntimeEvent(
                event_type="error",
                tool_call_id=call.tool_call_id,
                tool_name=call.tool_name,
                error=ErrorInfo(
                    error_code=hooked.error_code,
                    error_message=hooked.message,
                    retryable=hooked.retryable,
                ),
            )
        )
        spec = self._safe_spec(call.tool_name)
        return self._finalize_error(spec, call, actor, started_at, attempt=0, error=hooked)

    def _finalize_success(
        self,
        spec: ToolSpec,
        call: ToolCall,
        actor: str,
        started_at: float,
        attempt: int,
        output: dict[str, Any],
    ) -> ToolResult:
        """收尾成功结果并持久化。

        Args:
            spec: 工具规格。
            call: 当前工具调用。
            actor: 执行主体。
            started_at: 执行起始时间。
            attempt: 当前尝试次数。
            output: 工具输出。

        Returns:
            ToolResult: 结构化成功结果。
        """
        result = ToolResult(
            tool_call_id=call.tool_call_id,
            status="ok",
            output=output,
            latency_ms=int((monotonic() - started_at) * 1000),
        )
        result = self.hooks.after_execute(result)
        self.persist_result(spec, call, actor, result)
        self.hooks.emit_event(
            ToolRuntimeEvent(
                event_type="after_execute",
                tool_call_id=call.tool_call_id,
                tool_name=call.tool_name,
                attempt=attempt,
                latency_ms=result.latency_ms,
                payload={"status": result.status},
            )
        )
        return result

    def _finalize_error(
        self,
        spec: ToolSpec,
        call: ToolCall,
        actor: str,
        started_at: float,
        attempt: int,
        error: ToolRuntimeError,
    ) -> ToolResult:
        """收尾失败结果并持久化。

        Args:
            spec: 工具规格。
            call: 当前工具调用。
            actor: 执行主体。
            started_at: 执行起始时间。
            attempt: 当前尝试次数。
            error: 归一化错误对象。

        Returns:
            ToolResult: 结构化失败结果。
        """

        result = self._build_error_result(call, started_at, error)
        result = self.hooks.after_execute(result)
        self.persist_result(spec, call, actor, result)
        self.hooks.emit_event(
            ToolRuntimeEvent(
                event_type="after_execute",
                tool_call_id=call.tool_call_id,
                tool_name=call.tool_name,
                attempt=attempt,
                latency_ms=result.latency_ms,
                payload={"status": result.status},
                error=result.error,
            )
        )
        return result

    # ------------------------------------------------------------------
    # 私有：工具验证与调度
    # ------------------------------------------------------------------

    def _safe_spec(self, tool_name: str) -> ToolSpec:
        """安全解析 ToolSpec，失败时返回降级规格。

        Args:
            tool_name: 工具名称。

        Returns:
            ToolSpec: 真实规格或最小降级规格。
        """
        try:
            return self.resolve_spec(tool_name)
        except ToolRuntimeError:
            return ToolSpec(name=tool_name)

    def _check_capabilities(self, spec: ToolSpec, capabilities: set[str]) -> None:
        """校验工具能力授权。

        Args:
            spec: 工具规格。
            capabilities: 当前调用方能力集合。

        Raises:
            ToolRuntimeError: 缺少必需能力时抛出。
        """
        if not spec.required_capabilities:
            return
        missing = sorted(spec.required_capabilities - capabilities)
        if missing:
            raise ToolRuntimeError("TOOL_PERMISSION_DENIED", f"缺少工具能力: {missing}")

    def _validate_args(self, spec: ToolSpec, args: dict[str, Any]) -> None:
        """校验调用参数是否符合 ToolSpec.args_schema（JSON Schema 子集）。

        Args:
            spec: 工具规格，包含 args_schema。
            args: 调用参数。

        Raises:
            ToolRuntimeError: 参数不满足 schema 约束时抛出。
        支持的约束：type、required、additionalProperties、enum、
        minimum/maximum（数值）、minLength/maxLength（字符串）、pattern（字符串正则）。
        """
        schema = spec.args_schema
        if not schema:
            return
        if schema.get("type") not in {None, "object"}:
            raise ToolRuntimeError("TOOL_VALIDATION_ERROR", "仅支持 object 参数定义")

        for key in schema.get("required", []):
            if key not in args:
                raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"缺少必填参数: {key}")

        properties = schema.get("properties", {})
        additional_properties = schema.get("additionalProperties", True)
        if additional_properties is False:
            unknown_keys = sorted(set(args.keys()) - set(properties.keys()))
            if unknown_keys:
                raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"存在未声明参数: {unknown_keys}")

        for key, value in args.items():
            if key not in properties:
                continue
            prop = properties[key]
            expected_type = prop.get("type")
            if expected_type and not _is_expected_type(value, expected_type):
                raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"参数类型错误: {key} 期望 {expected_type}")

            # enum 约束
            if "enum" in prop and value not in prop["enum"]:
                raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"参数值不在枚举范围: {key}={value!r}, 允许值: {prop['enum']}")

            # 数值范围约束
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if "minimum" in prop and value < prop["minimum"]:
                    raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"参数值过小: {key}={value}, 最小值: {prop['minimum']}")
                if "maximum" in prop and value > prop["maximum"]:
                    raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"参数值过大: {key}={value}, 最大值: {prop['maximum']}")

            # 字符串长度与正则约束
            if isinstance(value, str):
                if "minLength" in prop and len(value) < prop["minLength"]:
                    raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"参数字符串过短: {key}, 最小长度: {prop['minLength']}")
                if "maxLength" in prop and len(value) > prop["maxLength"]:
                    raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"参数字符串过长: {key}, 最大长度: {prop['maxLength']}")
                if "pattern" in prop and not re.fullmatch(prop["pattern"], value):
                    raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"参数不符合正则约束: {key}, pattern: {prop['pattern']}")

    def _run_with_timeout_sync(self, handler: ToolHandler, args: dict[str, Any], timeout_ms: int) -> dict[str, Any]:
        """同步超时执行。

        Args:
            handler: 工具处理函数。
            args: 工具参数。
            timeout_ms: 超时时间（毫秒）。

        Returns:
            dict[str, Any]: 工具输出。

        Raises:
            ToolRuntimeError: 超时、输出格式错误或执行异常时抛出。
        注意：超时依赖 ThreadPoolExecutor.future.result(timeout)，属于"尽力而为"超时——
        超时触发后工作线程仍在后台继续运行直至完成，无法强制中断。
        如需严格超时隔离，请使用异步路径 execute_async（底层 asyncio.wait_for 可取消协程）。

        对于 async handler：在工作线程内新建独立事件循环执行，避免与调用方已有事件循环冲突
        （直接调用 asyncio.run() 在已有 loop 中会抛 RuntimeError）。
        """
        timeout_seconds = max(0.001, timeout_ms / 1000.0)

        def _invoke() -> dict[str, Any]:
            result = handler(args)
            if inspect.isawaitable(result):
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(result)
                finally:
                    loop.close()
            if not isinstance(result, dict):
                raise ToolRuntimeError("TOOL_EXECUTION_ERROR", "工具输出必须为 dict")
            return result

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_invoke)
                return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError as exc:
            raise ToolRuntimeError("TOOL_TIMEOUT", f"工具执行超时({timeout_ms}ms)", retryable=True) from exc
        except ToolRuntimeError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ToolRuntimeError("TOOL_EXECUTION_ERROR", f"工具执行异常: {exc}") from exc

    async def _run_with_timeout_async(self, handler: ToolHandler, args: dict[str, Any], timeout_ms: int) -> dict[str, Any]:
        """异步超时执行。

        Args:
            handler: 工具处理函数。
            args: 工具参数。
            timeout_ms: 超时时间（毫秒）。

        Returns:
            dict[str, Any]: 工具输出。

        Raises:
            ToolRuntimeError: 超时、输出格式错误或执行异常时抛出。
        """
        timeout_seconds = max(0.001, timeout_ms / 1000.0)

        async def _invoke() -> dict[str, Any]:
            if inspect.iscoroutinefunction(handler):
                result = await handler(args)  # type: ignore[misc]
            else:
                result = await asyncio.to_thread(handler, args)
                if inspect.isawaitable(result):
                    result = await result
            if not isinstance(result, dict):
                raise ToolRuntimeError("TOOL_EXECUTION_ERROR", "工具输出必须为 dict")
            return result

        try:
            return await asyncio.wait_for(_invoke(), timeout=timeout_seconds)
        except asyncio.TimeoutError as exc:
            raise ToolRuntimeError("TOOL_TIMEOUT", f"工具执行超时({timeout_ms}ms)", retryable=True) from exc
        except ToolRuntimeError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ToolRuntimeError("TOOL_EXECUTION_ERROR", f"工具执行异常: {exc}") from exc

    def _build_error_result(self, tool_call: ToolCall, started_at: float, error: ToolRuntimeError) -> ToolResult:
        """构建标准化失败结果。

        Args:
            tool_call: 当前工具调用。
            started_at: 执行起始时间。
            error: 已归一化错误对象。

        Returns:
            ToolResult: 标准化失败结果。
        """
        return ToolResult(
            tool_call_id=tool_call.tool_call_id,
            status="error",
            output={},
            latency_ms=int((monotonic() - started_at) * 1000),
            error=ErrorInfo(error_code=error.error_code, error_message=error.message, retryable=error.retryable),
        )


def _is_expected_type(value: Any, expected_type: str) -> bool:
    """判断值是否匹配 JSON Schema 基础类型。

    Args:
        value: 待校验值。
        expected_type: 期望类型字符串。

    Returns:
        bool: 匹配返回 True，否则 False。
    """
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return (isinstance(value, int) and not isinstance(value, bool)) or isinstance(value, float)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "object":
        return isinstance(value, dict)
    return True
