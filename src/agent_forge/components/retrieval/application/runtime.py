"""Retrieval 运行时。"""

from __future__ import annotations

from agent_forge.components.retrieval.application.bridges import build_citations_from_hits
from agent_forge.components.retrieval.domain import RetrievalHit, RetrievalQuery, RetrievalResult, Reranker, Retriever


class RetrievalRuntime:
    """编排检索与重排流水线。"""

    def __init__(self, retriever: Retriever, reranker: Reranker | None = None) -> None:
        """初始化检索运行时。

        Args:
            retriever: 检索器实现。
            reranker: 可选重排器实现。

        Returns:
            None.
        """

        self._retriever = retriever
        self._reranker = reranker

    def search(self, query: RetrievalQuery) -> RetrievalResult:
        """执行检索流水线并返回标准化结果。

        Args:
            query: 标准化检索请求。

        Returns:
            RetrievalResult: 标准化检索结果。
        """

        # 1. 先调用检索器拿到原始候选，保留候选总量用于后续评测与审计。
        raw_hits = self._retriever.retrieve(query)
        total_candidates = len(raw_hits)

        # 2. 在运行时统一执行最小分数过滤，避免把这个规则绑死到任一后端。
        filtered_hits = _apply_score_filter(raw_hits, query.min_score)

        # 3. 若配置了重排器，则在统一抽象层执行重排；否则走直通路径。
        ranked_hits = filtered_hits if self._reranker is None else self._reranker.rerank(query, filtered_hits)

        # 4. 最终在运行时统一裁到 top_k 并写入 rank，保证不同后端输出形状一致。
        final_hits = _normalize_ranks(ranked_hits[: query.top_k])

        # 5. 用最终命中构造标准化 citations，形成可直接交给上下文工程的桥接结果。
        citations = build_citations_from_hits(final_hits)
        reranker_version = "none" if self._reranker is None else self._reranker.reranker_version

        return RetrievalResult(
            hits=final_hits,
            citations=citations,
            backend_name=self._retriever.backend_name,
            retriever_version=self._retriever.retriever_version,
            reranker_version=reranker_version,
            total_candidates=total_candidates,
        )


def _apply_score_filter(hits: list[RetrievalHit], min_score: float | None) -> list[RetrievalHit]:
    """按最小分数过滤命中列表。

    Args:
        hits: 原始命中列表。
        min_score: 最低分数阈值。

    Returns:
        list[RetrievalHit]: 过滤后的命中列表。
    """

    if min_score is None:
        return [item.model_copy(deep=True) for item in hits]
    return [item.model_copy(deep=True) for item in hits if item.score >= min_score]


def _normalize_ranks(hits: list[RetrievalHit]) -> list[RetrievalHit]:
    """重写最终 rank，保证排序名次稳定。

    Args:
        hits: 待写入 rank 的命中列表。

    Returns:
        list[RetrievalHit]: 带稳定 rank 的命中列表。
    """

    output: list[RetrievalHit] = []
    for index, hit in enumerate(hits, start=1):
        copied = hit.model_copy(deep=True)
        copied.rank = index
        output.append(copied)
    return output
