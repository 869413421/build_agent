"""Provider 适配器抽象与通用实现。"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from typing import Any

import openai

from agent_forge.components.model_runtime.domain.schemas import (
    ModelAuthenticationError,
    ModelError,
    ModelRateLimitError,
    ModelRequest,
    ModelResponse,
    ModelStats,
    ModelTimeoutError,
)
from agent_forge.components.protocol import ToolCall
from agent_forge.support.logging import get_logger

logger = get_logger(__name__)


class ProviderAdapter(ABC):
    """模型厂商统一适配层接口。"""

    @abstractmethod
    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        """执行模型调用。"""
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

        if request.response_schema:
            schema_name = merged_kwargs.pop("request_id", "model_runtime_schema")
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "schema": request.response_schema,
                },
            }

        timeout_ms = merged_kwargs.pop("timeout_ms", None)
        if timeout_ms is not None:
            payload["timeout"] = timeout_ms / 1000

        payload.update(merged_kwargs)
        return payload

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

