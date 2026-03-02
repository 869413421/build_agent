"""OpenAI 真实适配器实现。"""

from __future__ import annotations

from typing import Any

from agent_forge.components.model_runtime.infrastructure.adapters.base import OpenAICompatibleAdapter
from agent_forge.support.config import settings


class OpenAIAdapter(OpenAICompatibleAdapter):
    """OpenAI 官方 API 适配器。"""

    provider_name = "openai"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None, client: Any | None = None):
        super().__init__(
            api_key=api_key or settings.openai_api_key,
            base_url=base_url or settings.openai_base_url,
            default_model=model or settings.openai_model,
            client=client,
        )

