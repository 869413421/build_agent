"""离线测试用适配器。"""

from __future__ import annotations

import time
from collections.abc import Iterator

from agent_forge.components.model_runtime.infrastructure.adapters.base import ProviderAdapter
from agent_forge.components.model_runtime.domain.schemas import ModelRequest, ModelResponse, ModelStats, ModelStreamEvent


class StubOpenAIAdapter(ProviderAdapter):
    """OpenAI 存根实现（用于测试和示例）。"""

    def __init__(self, mock_response: str | None = None, mock_cost_per_1k: float = 0.002):
        self.mock_response = mock_response or '{"status": "ok", "message": "hello from openai"}'
        self.mock_cost_per_1k = mock_cost_per_1k

    def generate(self, request: ModelRequest, **kwargs: object) -> ModelResponse:
        # 1. 模拟生成延迟与 成本
        prompt_t = 100
        completion_t = 50
        cost = ((prompt_t + completion_t) / 1000.0) * self.mock_cost_per_1k
        # 2. 返回标准化响应
        return ModelResponse(
            content=self.mock_response,
            stats=ModelStats(
                prompt_tokens=prompt_t,
                completion_tokens=completion_t,
                total_tokens=prompt_t + completion_t,
                latency_ms=150,
                cost_usd=cost,
            ),
        )

    def generate_stream(self, request: ModelRequest, **kwargs: object) -> Iterator[ModelStreamEvent]:
        request_id = request.request_id or f"req_stub_{int(time.time() * 1000)}"
        seq = 0
        now_ms = int(time.time() * 1000)
        yield ModelStreamEvent(event_type="start", request_id=request_id, sequence=seq, timestamp_ms=now_ms)
        seq += 1

        chunk_size = 8
        for idx in range(0, len(self.mock_response), chunk_size):
            part = self.mock_response[idx : idx + chunk_size]
            yield ModelStreamEvent(
                event_type="delta",
                request_id=request_id,
                sequence=seq,
                delta=part,
                timestamp_ms=int(time.time() * 1000),
            )
            seq += 1

        stats = ModelStats(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_ms=150,
            cost_usd=((100 + 50) / 1000.0) * self.mock_cost_per_1k,
        )
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
            content=self.mock_response,
            stats=stats,
            timestamp_ms=int(time.time() * 1000),
            metadata={"status": "ok"},
        )


class StubDeepSeekAdapter(ProviderAdapter):
    """DeepSeek 存根实现（用于测试和示例）。"""

    def __init__(self, mock_response: str | None = None, mock_cost_per_1k: float = 0.001):
        self.mock_response = mock_response or '{"status": "ok", "message": "hello from deepseek"}'
        self.mock_cost_per_1k = mock_cost_per_1k

    def generate(self, request: ModelRequest, **kwargs: object) -> ModelResponse:
        # 1. 模拟生成延迟与 成本
        prompt_t = 80
        completion_t = 40
        cost = ((prompt_t + completion_t) / 1000.0) * self.mock_cost_per_1k
        # 2. 返回标准化响应
        return ModelResponse(
            content=self.mock_response,
            stats=ModelStats(
                prompt_tokens=prompt_t,
                completion_tokens=completion_t,
                total_tokens=prompt_t + completion_t,
                latency_ms=120,
                cost_usd=cost,
            ),
        )

    def generate_stream(self, request: ModelRequest, **kwargs: object) -> Iterator[ModelStreamEvent]:
        request_id = request.request_id or f"req_stub_{int(time.time() * 1000)}"
        seq = 0
        yield ModelStreamEvent(
            event_type="start",
            request_id=request_id,
            sequence=seq,
            timestamp_ms=int(time.time() * 1000),
        )
        seq += 1
        chunk_size = 8
        for idx in range(0, len(self.mock_response), chunk_size):
            part = self.mock_response[idx : idx + chunk_size]
            yield ModelStreamEvent(
                event_type="delta",
                request_id=request_id,
                sequence=seq,
                delta=part,
                timestamp_ms=int(time.time() * 1000),
            )
            seq += 1
        stats = ModelStats(
            prompt_tokens=80,
            completion_tokens=40,
            total_tokens=120,
            latency_ms=120,
            cost_usd=((80 + 40) / 1000.0) * self.mock_cost_per_1k,
        )
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
            content=self.mock_response,
            stats=stats,
            timestamp_ms=int(time.time() * 1000),
            metadata={"status": "ok"},
        )


