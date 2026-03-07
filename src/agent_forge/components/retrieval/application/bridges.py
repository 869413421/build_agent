"""Retrieval 与上下游组件的桥接工具。"""

from __future__ import annotations

from agent_forge.components.context_engineering import CitationItem
from agent_forge.components.retrieval.domain import RetrievedCitation, RetrievalHit


def build_citations_from_hits(hits: list[RetrievalHit], max_snippet_chars: int = 240) -> list[RetrievedCitation]:
    """从命中列表构造标准化引用。

    Args:
        hits: 最终命中列表。
        max_snippet_chars: 摘要截断长度。

    Returns:
        list[RetrievedCitation]: 标准化引用列表。
    """

    citations: list[RetrievedCitation] = []
    for hit in hits:
        document = hit.document
        snippet = document.content[:max_snippet_chars].strip()
        citations.append(
            RetrievedCitation(
                document_id=document.document_id,
                title=document.title or document.document_id,
                source_uri=document.source_uri,
                snippet=snippet,
                score=hit.score,
            )
        )
    return citations


def to_context_citations(citations: list[RetrievedCitation]) -> list[CitationItem]:
    """转换为 Context Engineering 使用的引用结构。

    Args:
        citations: Retrieval 标准化引用列表。

    Returns:
        list[CitationItem]: 上下文工程引用列表。
    """

    output: list[CitationItem] = []
    for item in citations:
        output.append(
            CitationItem(
                source_id=item.document_id,
                title=item.title or item.document_id,
                url=item.source_uri or item.document_id,
                snippet=item.snippet,
                score=item.score,
            )
        )
    return output
