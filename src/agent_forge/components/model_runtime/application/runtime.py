"""Model Runtime 组件（防崩塌控制层）。

主要能力：
1. 依赖注入调度不同的 Adapter
2. JSON 结构化输出校验
3. 自动化的自愈重试链路
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

from agent_forge.components.model_runtime.infrastructure.adapters import ProviderAdapter
from agent_forge.components.model_runtime.domain.schemas import (
    ModelError,
    ModelParseError,
    ModelRequest,
    ModelResponse,
    ModelRuntimeHooks,
    ModelStreamEvent,
    ModelStats,
    NoopModelRuntimeHooks,
)
from agent_forge.components.protocol import AgentMessage
from agent_forge.support.logging import get_logger

logger = get_logger(__name__)


class ModelRuntime:
    """负责大模型调用的防御性执行环境。"""

    def __init__(self, adapter: ProviderAdapter, max_retries: int = 2):
        self.adapter = adapter
        self.max_retries = max_retries
        self.last_stream_response: ModelResponse | None = None

    def generate(
        self,
        request: ModelRequest,
        hooks: ModelRuntimeHooks | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """执行带防御控制的生成流程。"""

        active_hooks = hooks or NoopModelRuntimeHooks()

        # 1. 记录初始系统请求信息
        attempt = 0
        last_error: Exception | None = None
        current_request = active_hooks.before_request(request.model_copy(deep=True))

        # 2. 进入带重试机制的调用循环
        while attempt <= self.max_retries:
            try:
                # 3. 委派给具体的厂商 Adapter
                response = self.adapter.generate(current_request, **kwargs)

                # 4. 如果没有结构化输出要求，直接返回
                if not current_request.response_schema:
                    return active_hooks.after_response(response)

                # 5. 尝试将返回的字符串解析为结构化 JSON
                # 实际生产中可能需要配合 Pydantic model_validate
                try:
                    parsed_data = self._parse_json(response.content)
                    
                    # 非常基础的结构匹配检查 (如果 schema 要求字段存在)
                    self._validate_against_schema(parsed_data, current_request.response_schema)
                    
                    response.parsed_output = parsed_data
                    return active_hooks.after_response(response)

                except json.JSONDecodeError as json_exc:
                    raise ModelParseError(f"JSON 格式非法: {json_exc}", raw_content=response.content) from json_exc
                except ValueError as val_exc:
                    raise ModelParseError(f"缺少必须结构: {val_exc}", raw_content=response.content) from val_exc

            except ModelError as err:
                last_error = err
                # 6. 非可重试错误或达到重试上限，直接抛出
                if not err.retryable or attempt >= self.max_retries:
                    logger.error(f"模型调用失败，超出重试次数或无法重试: {err.error_code}")
                    raise err

                logger.warning(f"由于 {err.error_code} 开启自愈重试 (attempt {attempt + 1}/{self.max_retries})")
                
                # 7. 自愈重试：构建修复提示并重试
                if isinstance(err, ModelParseError):
                    repair_msg = AgentMessage(
                        role="user",
                        content=(
                            f"你上次的输出无法解析为合法的 JSON 或未满足所需结构限制。\n"
                            f"错误原因: {err.message}\n"
                            f"你上次的原始内容:\n{err.raw_content}\n"
                            f"请按照要求的 JSON schema 纠正输出格式并仅输出有效 JSON。"
                        ),
                    )
                    current_request.messages.append(repair_msg)
                
                attempt += 1

        # 若达到上限依然退出，提供兜底防范。由于逻辑上有 `if attempt >= max_retries: raise` 保护，原则上这里不会触达。
        raise last_error or RuntimeError("模型循环执行异常到达不可能分支")

    def stream_generate(
        self,
        request: ModelRequest,
        hooks: ModelRuntimeHooks | None = None,
        **kwargs: Any,
    ) -> Iterator[ModelStreamEvent]:
        """Run streaming generation and emit normalized events."""

        active_hooks = hooks or NoopModelRuntimeHooks()
        prepared = request.model_copy(deep=True)
        if not prepared.request_id:
            prepared.request_id = f"req_{uuid4().hex}"
        prepared = active_hooks.before_request(prepared)

        stream_iter = self.adapter.generate_stream(prepared, **kwargs)
        full_parts: list[str] = []
        final_stats: ModelStats | None = None
        final_content = ""

        try:
            for event in stream_iter:
                patched = active_hooks.on_stream_event(event)
                if patched.event_type == "delta" and patched.delta:
                    full_parts.append(patched.delta)
                if patched.event_type == "usage" and patched.stats:
                    final_stats = patched.stats
                if patched.event_type == "end":
                    if patched.content is not None:
                        final_content = patched.content
                    if patched.stats is not None:
                        final_stats = patched.stats
                yield patched
        finally:
            closer = getattr(stream_iter, "close", None)
            if callable(closer):
                closer()

        if not final_content:
            final_content = "".join(full_parts)
        response = ModelResponse(
            content=final_content,
            stats=final_stats or ModelStats(),
        )
        if prepared.response_schema and response.content:
            parsed_data = self._parse_json(response.content)
            self._validate_against_schema(parsed_data, prepared.response_schema)
            response.parsed_output = parsed_data

        self.last_stream_response = active_hooks.after_response(response)

    def _parse_json(self, raw_content: str) -> dict[str, Any]:
        """清理 markdown code block 并解析 JSON。"""

        content = raw_content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
            
        if content.endswith("```"):
            content = content[:-3]
            
        return json.loads(content.strip())

    def _validate_against_schema(self, data: dict[str, Any], schema: dict[str, Any]) -> None:
        """非常轻量级的 schema 验证（生产中通常会交由 Pydantic 执行）。"""

        required_keys = schema.get("required", [])
        missing_keys = [k for k in required_keys if k not in data]
        if missing_keys:
            raise ValueError(f"缺少必填列: {missing_keys}")



