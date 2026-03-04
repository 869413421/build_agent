"""共享测试夹具。"""

from __future__ import annotations

import pytest


class FakeTavilyClient:
    """Tavily 客户端假实现，供单测离线使用。"""

    def search(self, **kwargs: object) -> dict:
        return {
            "query": kwargs.get("query"),
            "results": [
                {"title": "Doc1", "url": "https://example.com/1", "content": "c1", "score": 0.9},
                {"title": "Doc2", "url": "https://example.com/2", "content": "c2", "score": 0.8},
            ],
        }


@pytest.fixture
def fake_tavily_client() -> FakeTavilyClient:
    return FakeTavilyClient()
