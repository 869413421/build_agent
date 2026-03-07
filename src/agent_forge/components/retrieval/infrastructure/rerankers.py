"""Retrieval 基线重排器。"""

from __future__ import annotations

from agent_forge.components.retrieval.domain import RetrievalHit, RetrievalQuery


class NoopReranker:
    """不改变顺序的基线重排器。"""

    reranker_name = "noop"
    reranker_version = "none"

    def rerank(self, query: RetrievalQuery, hits: list[RetrievalHit]) -> list[RetrievalHit]:
        """直接返回原始顺序。

        Args:
            query: 标准化检索请求。
            hits: 原始命中列表。

        Returns:
            list[RetrievalHit]: 与输入顺序一致的命中列表。
        """

        return [item.model_copy(deep=True) for item in hits]
