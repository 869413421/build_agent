"""DeepSeek 真实适配器实现。"""

from __future__ import annotations

from typing import Any

from agent_forge.components.model_runtime.infrastructure.adapters.base import OpenAICompatibleAdapter
from agent_forge.support.config import settings


class DeepSeekAdapter(OpenAICompatibleAdapter):
    """DeepSeek API 适配器（OpenAI 兼容协议）。"""

    provider_name = "deepseek"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        client: Any | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key or settings.deepseek_api_key,
            base_url=base_url or settings.deepseek_base_url,
            default_model=model or settings.deepseek_model,
            client=client,
        )

