"""离线测试用适配器。"""

from __future__ import annotations

from agent_forge.components.model_runtime.infrastructure.adapters.base import ProviderAdapter
from agent_forge.components.model_runtime.domain.schemas import ModelRequest, ModelResponse, ModelStats


class StubOpenAIAdapter(ProviderAdapter):
    """OpenAI 存根实现（用于测试和示例）。"""

    def __init__(self, mock_response: str | None = None, mock_cost_per_1k: float = 0.002):
        self.mock_response = mock_response or '{"status": "ok", "message": "hello from openai"}'
        self.mock_cost_per_1k = mock_cost_per_1k

    def generate(self, request: ModelRequest, **kwargs: object) -> ModelResponse:
        # 1. 模拟生成延迟与 Cost
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


class StubDeepSeekAdapter(ProviderAdapter):
    """DeepSeek 存根实现（用于测试和示例）。"""

    def __init__(self, mock_response: str | None = None, mock_cost_per_1k: float = 0.001):
        self.mock_response = mock_response or '{"status": "ok", "message": "hello from deepseek"}'
        self.mock_cost_per_1k = mock_cost_per_1k

    def generate(self, request: ModelRequest, **kwargs: object) -> ModelResponse:
        # 1. 模拟生成延迟与 Cost
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

