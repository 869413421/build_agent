"""Tavily 搜索工具。"""

from __future__ import annotations

from typing import Any

from agent_forge.components.tool_runtime.domain.schemas import ToolRuntimeError, ToolSpec
from agent_forge.support.config import settings


class TavilySearchTool:
    """基于 Tavily 官方 SDK 的搜索工具。"""

    def __init__(self, api_key: str | None = None, client: Any | None = None) -> None:
        """初始化 Tavily 工具。

        Args:
            api_key: 可选 API Key；为空时从 settings 读取。
            client: 可选已构建 Tavily 客户端；用于测试注入。
        """

        self._api_key = api_key or settings.tavily_api_key
        self._client = client

    @property
    def tool_spec(self) -> ToolSpec:
        """返回适合 `AgentApp` 注册的工具规格。"""

        return ToolSpec(
            name="web_search",
            description="通过 Tavily 执行联网搜索并返回标准化结果。",
            args_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"},
                    "search_depth": {"type": "string"},
                    "topic": {"type": "string"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            side_effect_level="low",
        )

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        """执行 Tavily 搜索。

        Args:
            args: 输入参数，至少包含 `query`；可选 `max_results/search_depth/topic`。

        Returns:
            dict[str, Any]: 标准化搜索结果。

        Raises:
            ToolRuntimeError: 参数不合法或调用失败时抛出。
        """

        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ToolRuntimeError("TOOL_VALIDATION_ERROR", "query 必须是非空字符串")

        max_results_raw = args.get("max_results", 5)
        try:
            max_results = int(max_results_raw)
        except (TypeError, ValueError):
            raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"max_results 必须为整数，收到: {max_results_raw!r}")
        search_depth = str(args.get("search_depth", "basic"))
        topic = str(args.get("topic", "general"))

        # 1. 构建客户端：优先使用注入 client，便于单测和离线验证。
        client = self._client or self._build_client()
        try:
            # 2. 调用 SDK：保持最小参数集合，避免示例 API 过度复杂化。
            raw = client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                topic=topic,
            )
        except ToolRuntimeError:
            raise
        except Exception as exc:  # noqa: BLE001
            # 3. 错误映射：SDK/网络异常统一收口到 ToolRuntimeError。
            raise ToolRuntimeError("TOOL_EXECUTION_ERROR", f"Tavily 调用失败: {exc}", retryable=True) from exc

        results = raw.get("results", []) if isinstance(raw, dict) else []
        normalized: list[dict[str, Any]] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score"),
                }
            )

        return {
            "query": query,
            "results": normalized,
            "result_count": len(normalized),
            "raw_response": raw if isinstance(raw, dict) else {"raw": str(raw)},
        }

    def _build_client(self) -> Any:
        """构建 Tavily 客户端。

        Returns:
            Any: Tavily SDK 客户端实例。

        Raises:
            ToolRuntimeError: 缺少密钥或 SDK 不可用时抛出。
        """

        if not self._api_key:
            raise ToolRuntimeError("TOOL_EXECUTION_ERROR", "缺少 AF_TAVILY_API_KEY", retryable=False)
        try:
            from tavily import TavilyClient
        except Exception as exc:  # noqa: BLE001
            raise ToolRuntimeError(
                "TOOL_EXECUTION_ERROR",
                "未安装 tavily SDK，请执行 uv sync --dev",
                retryable=False,
            ) from exc
        return TavilyClient(api_key=self._api_key)


def build_tavily_search_handler(tool: TavilySearchTool | None = None):
    """构建可注册到 ToolRuntime 的 handler。

    Args:
        tool: 可选工具实例；为空时创建默认实例。

    Returns:
        Callable[[dict[str, Any]], dict[str, Any]]: 可直接注册的处理函数。
    """

    active_tool = tool or TavilySearchTool()
    return active_tool.execute
