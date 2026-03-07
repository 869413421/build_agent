"""Provider 适配器抽象与通用实现。"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

import openai

from agent_forge.components.model_runtime.domain.schemas import (
    ModelAuthenticationError,
    ModelError,
    ModelRateLimitError,
    ModelRequest,
    ModelResponse,
    ModelStreamEvent,
    ModelStats,
    ModelTimeoutError,
)
from agent_forge.components.protocol import ErrorInfo, ToolCall
from agent_forge.support.logging import get_logger

logger = get_logger(__name__)

_INTERNAL_REQUEST_EXTRA_KEYS = {
    # Internal context-engineering diagnostics should never be sent to providers.
    "context_budget_report",
    # Context-engineering input-only helpers.
    "citations",
    # Canonical tools should come from ModelRequest.tools field, not extra kwargs.
    "tools",
}


class ProviderAdapter(ABC):
    """模型厂商统一适配层接口。"""

    @abstractmethod
    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        """执行模型调用。"""
        raise NotImplementedError

    @abstractmethod
    def generate_stream(self, request: ModelRequest, **kwargs: Any) -> Iterator[ModelStreamEvent]:
        """执行流式模型调用。"""
        raise NotImplementedError


class OpenAICompatibleAdapter(ProviderAdapter):
    """OpenAI 兼容协议适配器基类。"""

    provider_name: str = "openai-compatible"

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        default_model: str,
        client: Any | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model
        if not self.api_key:
            logger.warning("%s 未提供 API Key，调用时可能鉴权失败。", self.provider_name)
        self.client = client or openai.Client(api_key=self.api_key, base_url=self.base_url)

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        payload = self._build_payload(request, **kwargs)
        start_t = time.monotonic()
        try:
            raw_response = self.client.chat.completions.create(**payload)
        except openai.BadRequestError as exc:
            # 某些兼容服务不支持 json_schema，这里自动降级为 json_object 再试一次。
            if request.response_schema and self._is_response_format_unavailable(exc):
                logger.warning("%s response_format 不可用，自动降级为 json_object 重试。", self.provider_name)
                fallback_payload = self._build_payload(
                    request,
                    response_format={"type": "json_object"},
                    **kwargs,
                )
                raw_response = self.client.chat.completions.create(**fallback_payload)
            else:
                # BadRequest 通常是参数不被模型支持，重试不会自愈。
                raise ModelError(error_code=f"{self.provider_name.upper()}_BAD_REQUEST", message=str(exc), retryable=False) from exc
        except openai.AuthenticationError as exc:
            raise ModelAuthenticationError(str(exc)) from exc
        except openai.RateLimitError as exc:
            raise ModelRateLimitError(str(exc)) from exc
        except openai.APITimeoutError as exc:
            raise ModelTimeoutError(str(exc)) from exc
        except openai.OpenAIError as exc:
            raise ModelError(error_code=f"{self.provider_name.upper()}_ERROR", message=str(exc), retryable=True) from exc

        latency_ms = int((time.monotonic() - start_t) * 1000)
        choice = raw_response.choices[0]
        usage = raw_response.usage
        return ModelResponse(
            content=(choice.message.content or "").strip(),
            tool_calls=self._extract_tool_calls(choice.message),
            stats=ModelStats(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                latency_ms=latency_ms,
            ),
        )

    def generate_stream(self, request: ModelRequest, **kwargs: Any) -> Iterator[ModelStreamEvent]:
        request_id = request.request_id or kwargs.get("request_id") or f"req_{int(time.time() * 1000)}"
        payload = self._build_payload(request, stream=True, **kwargs)
        seq = 0
        start_ms = int(time.time() * 1000)
        started_at = time.monotonic()
        full_parts: list[str] = []
        stats = ModelStats()
        stream_obj: Any | None = None

        yield ModelStreamEvent(
            event_type="start",
            request_id=request_id,
            sequence=seq,
            timestamp_ms=start_ms,
            metadata={"provider": self.provider_name},
        )
        seq += 1

        try:
            stream_obj = self.client.chat.completions.create(**payload)
            for chunk in stream_obj:
                delta = self._extract_delta_content(chunk)
                if delta:
                    full_parts.append(delta)
                    yield ModelStreamEvent(
                        event_type="delta",
                        request_id=request_id,
                        sequence=seq,
                        delta=delta,
                        timestamp_ms=int(time.time() * 1000),
                    )
                    seq += 1
                usage = self._extract_usage(chunk)
                if usage:
                    stats = usage
        except Exception as exc:  # noqa: BLE001
            model_error = self._to_model_error(exc)
            elapsed_ms = int((time.monotonic() - started_at) * 1000)
            stats.latency_ms = elapsed_ms
            yield ModelStreamEvent(
                event_type="error",
                request_id=request_id,
                sequence=seq,
                timestamp_ms=int(time.time() * 1000),
                stats=stats,
                error=ErrorInfo(
                    error_code=model_error.error_code,
                    error_message=model_error.message,
                    retryable=model_error.retryable,
                ),
            )
            seq += 1
            yield ModelStreamEvent(
                event_type="end",
                request_id=request_id,
                sequence=seq,
                content="".join(full_parts),
                stats=stats,
                timestamp_ms=int(time.time() * 1000),
                metadata={"status": "error"},
            )
            return
        finally:
            closer = getattr(stream_obj, "close", None)
            if callable(closer):
                closer()

        stats.latency_ms = int((time.monotonic() - started_at) * 1000)
        yield ModelStreamEvent(
            event_type="usage",
            request_id=request_id,
            sequence=seq,
            stats=stats,
            timestamp_ms=int(time.time() * 1000),
        )
        seq += 1
        yield ModelStreamEvent(
            event_type="end",
            request_id=request_id,
            sequence=seq,
            content="".join(full_parts),
            stats=stats,
            timestamp_ms=int(time.time() * 1000),
            metadata={"status": "ok"},
        )

    def _build_payload(self, request: ModelRequest, **kwargs: Any) -> dict[str, Any]:
        messages: list[dict[str, Any]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})

        payload: dict[str, Any] = {
            "model": request.model or self.default_model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": request.stream,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.tools:
            payload["tools"] = request.tools

        merged_kwargs: dict[str, Any] = {}
        merged_kwargs.update(request.extra_kwargs())
        merged_kwargs.update(kwargs)
        merged_kwargs.pop("request_id", None)
        for key in _INTERNAL_REQUEST_EXTRA_KEYS:
            merged_kwargs.pop(key, None)

        response_format = merged_kwargs.pop("response_format", None)
        if request.response_schema:
            if response_format is None:
                schema_name = merged_kwargs.pop("request_id", "model_runtime_schema")
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "schema": request.response_schema,
                    },
                }
            else:
                payload["response_format"] = response_format
            # 无论使用 json_schema 还是 json_object，都加一层显式 JSON 约束，避免模型输出闲聊文本。
            payload["messages"].append(
                {
                    "role": "system",
                    "content": (
                        "请仅输出合法 JSON，且必须满足以下 JSON Schema：\n"
                        f"{json.dumps(request.response_schema, ensure_ascii=False)}"
                    ),
                }
            )

        timeout_ms = merged_kwargs.pop("timeout_ms", None)
        if timeout_ms is not None:
            payload["timeout"] = timeout_ms / 1000

        payload.update(merged_kwargs)
        return payload

    def _is_response_format_unavailable(self, exc: openai.BadRequestError) -> bool:
        text = str(exc).lower()
        return "response_format" in text and "unavailable" in text

    def _extract_tool_calls(self, message: Any) -> list[ToolCall]:
        tool_calls: list[ToolCall] = []
        raw_tool_calls = getattr(message, "tool_calls", None) or []
        for raw in raw_tool_calls:
            if isinstance(raw, dict):
                fn = raw.get("function", {})
                fn_name = fn.get("name")
                fn_args = fn.get("arguments", "{}")
                tool_id = raw.get("id")
            else:
                fn = getattr(raw, "function", None)
                fn_name = getattr(fn, "name", None)
                fn_args = getattr(fn, "arguments", "{}")
                tool_id = getattr(raw, "id", None)
            if fn_name and tool_id:
                try:
                    parsed_args = json.loads(fn_args) if isinstance(fn_args, str) else fn_args
                except Exception:
                    parsed_args = {"raw_arguments": fn_args}
                tool_calls.append(
                    ToolCall(
                        tool_call_id=tool_id,
                        tool_name=fn_name,
                        args=parsed_args,
                        principal="model",
                    )
                )
        return tool_calls

    def _to_model_error(self, exc: Exception) -> ModelError:
        if isinstance(exc, ModelError):
            return exc
        if isinstance(exc, openai.AuthenticationError):
            return ModelAuthenticationError(str(exc))
        if isinstance(exc, openai.RateLimitError):
            return ModelRateLimitError(str(exc))
        if isinstance(exc, openai.APITimeoutError):
            return ModelTimeoutError(str(exc))
        if isinstance(exc, openai.OpenAIError):
            return ModelError(
                error_code=f"{self.provider_name.upper()}_ERROR",
                message=str(exc),
                retryable=True,
            )
        return ModelError(
            error_code=f"{self.provider_name.upper()}_STREAM_ERROR",
            message=str(exc),
            retryable=False,
        )

    def _extract_delta_content(self, chunk: Any) -> str:
        choices = getattr(chunk, "choices", None)
        if not choices and isinstance(chunk, dict):
            choices = chunk.get("choices")
        if not choices:
            return ""

        first = choices[0]
        delta = getattr(first, "delta", None)
        if delta is None and isinstance(first, dict):
            delta = first.get("delta")

        content = getattr(delta, "content", None) if delta is not None else None
        if content is None and isinstance(delta, dict):
            content = delta.get("content")
        return content or ""

    def _extract_usage(self, chunk: Any) -> ModelStats | None:
        usage = getattr(chunk, "usage", None)
        if usage is None and isinstance(chunk, dict):
            usage = chunk.get("usage")
        if usage is None:
            return None
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)
        if isinstance(usage, dict):
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            total_tokens = usage.get("total_tokens")
        return ModelStats(
            prompt_tokens=prompt_tokens or 0,
            completion_tokens=completion_tokens or 0,
            total_tokens=total_tokens or 0,
        )

