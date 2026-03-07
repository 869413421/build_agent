"""Context Engineering 的 Token 估算与引用渲染辅助。"""

from __future__ import annotations

from typing import Any

from agent_forge.components.context_engineering.domain import CitationItem
from agent_forge.components.protocol import AgentMessage


class CharTokenEstimator:
    """基于 `chars/4` 的确定性 Token 估算器。"""

    _MIN_TOKENS = 1
    _MESSAGE_ROLE_OVERHEAD = 4

    def estimate_text(self, text: str) -> int:
        """估算纯文本 Token。

        Args:
            text: 输入文本。

        Returns:
            int: 估算 Token 数。
        """

        normalized = text.strip()
        if not normalized:
            return self._MIN_TOKENS
        return max(self._MIN_TOKENS, (len(normalized) + 3) // 4)

    def estimate_message(self, message: AgentMessage) -> int:
        """估算协议消息 Token。

        Args:
            message: 消息对象。

        Returns:
            int: 含角色开销的估算 Token 数。
        """

        return self._MESSAGE_ROLE_OVERHEAD + self.estimate_text(message.content)

    def estimate_tool(self, tool_schema: dict[str, Any]) -> int:
        """估算工具 schema Token。

        Args:
            tool_schema: 工具 schema 字典。

        Returns:
            int: 估算 Token 数。
        """

        return self.estimate_text(str(tool_schema))

    def estimate_citation(self, citation: CitationItem) -> int:
        """估算单条引用 Token。

        Args:
            citation: 引用条目。

        Returns:
            int: 估算 Token 数。
        """

        packed = f"{citation.title} {citation.url} {citation.snippet}"
        return self.estimate_text(packed)

    def estimate_citation_message(self, citations: list[CitationItem]) -> int:
        """估算“引用合成消息”的 Token。

        Args:
            citations: 将被渲染为消息的引用列表。

        Returns:
            int: 最终合成消息的估算 Token。
        """

        return self.estimate_message(build_citation_message(citations))

    def message_overhead_tokens(self) -> int:
        """返回消息固定开销 Token。

        Args:
            None.

        Returns:
            int: 固定消息开销 Token。
        """

        return self._MESSAGE_ROLE_OVERHEAD

    def truncate_text(self, text: str, max_tokens: int) -> str:
        """按给定预算截断文本。

        Args:
            text: 原始文本。
            max_tokens: 该文本可用 Token 预算。

        Returns:
            str: 截断后的文本；预算足够时保留截断标记。
        """

        marker = " ...(truncated)"
        max_chars = max(1, max_tokens * 4)
        if len(text) <= max_chars:
            return text
        if max_chars <= len(marker) + 1:
            return text[:max_chars]
        head_chars = max(1, max_chars - len(marker))
        return f"{text[:head_chars]}{marker}"


def format_citations_as_text(citations: list[CitationItem]) -> str:
    """把引用列表渲染为确定性的可读文本块。

    Args:
        citations: 引用条目列表。

    Returns:
        str: 渲染后的引用文本块。
    """

    lines = ["回答时请使用以下引用："]
    for index, citation in enumerate(citations, start=1):
        lines.append(f"[{index}] {citation.title}")
        lines.append(f"URL: {citation.url}")
        if citation.snippet:
            lines.append(f"Snippet: {citation.snippet}")
    return "\n".join(lines)


def build_citation_message(citations: list[CitationItem]) -> AgentMessage:
    """构建发送给模型的“引用合成消息”。

    Args:
        citations: 引用条目列表。

    Returns:
        AgentMessage: 含引用内容的 developer 消息。
    """

    return AgentMessage(role="developer", content=format_citations_as_text(citations))
