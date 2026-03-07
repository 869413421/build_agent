"""Retrieval 基础设施辅助函数。"""

from __future__ import annotations

from agent_forge.components.retrieval.domain import RetrievedDocument, RetrievalFilters


def matches_filters(document: RetrievedDocument, filters: RetrievalFilters) -> bool:
    """判断文档是否满足通用过滤条件。

    Args:
        document: 待判断文档。
        filters: 过滤条件。

    Returns:
        bool: 若满足过滤条件则返回 True。
    """

    if filters.document_ids and document.document_id not in filters.document_ids:
        return False
    if filters.source_uris and document.source_uri not in filters.source_uris:
        return False
    for key, value in filters.metadata_equals.items():
        if document.metadata.get(key) != value:
            return False
    return True
