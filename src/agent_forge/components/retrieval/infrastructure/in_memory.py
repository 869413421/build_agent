"""可离线运行的内存检索实现。"""

from __future__ import annotations

import re

from agent_forge.components.retrieval.domain import RetrievedDocument, RetrievalHit, RetrievalQuery
from agent_forge.components.retrieval.infrastructure.helpers import matches_filters


class InMemoryRetriever:
    """基于内存文档集的稳定检索器。"""

    def __init__(
        self,
        documents: list[RetrievedDocument],
        *,
        backend_name: str = "inmemory",
        retriever_version: str = "inmemory-v1",
    ) -> None:
        """初始化内存检索器。

        Args:
            documents: 预置文档集合。
            backend_name: 后端名称。
            retriever_version: 检索器版本。

        Returns:
            None.
        """

        self.backend_name = backend_name
        self.retriever_version = retriever_version
        self._documents = [item.model_copy(deep=True) for item in documents]

    def retrieve(self, query: RetrievalQuery) -> list[RetrievalHit]:
        """执行本地关键词检索。

        Args:
            query: 标准化检索请求。

        Returns:
            list[RetrievalHit]: 命中列表，按分数倒序排列。
        """

        # 1. 先做通用过滤，保证框架层 filters 语义在本地后端也成立。
        candidates = [doc for doc in self._documents if matches_filters(doc, query.filters)]
        query_terms = _tokenize(query.query_text)
        hits: list[RetrievalHit] = []

        # 2. 对每篇候选文档计算稳定分数；这里追求可预测，而不是追求检索效果最优。
        for document in candidates:
            score = _score_document(query.query_text, query_terms, document)
            if score <= 0:
                continue
            hits.append(
                RetrievalHit(
                    document=document.model_copy(deep=True),
                    score=score,
                )
            )

        # 3. 最终按分数和 document_id 稳定排序，避免测试与回放结果抖动。
        hits.sort(key=lambda item: (-item.score, item.document.document_id))
        return hits


def _tokenize(text: str) -> list[str]:
    """把文本拆成小写词元。

    Args:
        text: 原始文本。

    Returns:
        list[str]: 简单词元列表。
    """

    return [item for item in re.split(r"\W+", text.lower()) if item]


def _score_document(query_text: str, query_terms: list[str], document: RetrievedDocument) -> float:
    """计算内存检索分数。

    Args:
        query_text: 原始查询文本。
        query_terms: 查询词元列表。
        document: 候选文档。

        Returns:
            float: 稳定且可测试的命中分数。
    """

    haystack = f"{document.title} {document.content}".lower()
    if not haystack.strip():
        return 0.0
    if query_text.lower() in haystack:
        return 1.0
    if not query_terms:
        return 0.0
    matched = sum(1 for term in query_terms if term in haystack)
    return matched / len(query_terms)
