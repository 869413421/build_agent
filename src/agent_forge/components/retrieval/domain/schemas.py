"""Retrieval 领域模型定义。"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class RetrievalFilters(BaseModel):
    """通用检索过滤条件。"""

    document_ids: list[str] = Field(default_factory=list, description="限定可命中的文档 ID 列表。")
    source_uris: list[str] = Field(default_factory=list, description="限定可命中的来源 URI 列表。")
    metadata_equals: dict[str, Any] = Field(default_factory=dict, description="要求严格相等的元数据键值。")


class RetrievalQuery(BaseModel):
    """标准化检索请求。"""

    query_text: str = Field(..., min_length=1, description="检索查询文本。")
    top_k: int = Field(default=5, ge=1, description="返回命中数上限。")
    min_score: float | None = Field(default=None, description="最低可接受分数。")
    filters: RetrievalFilters = Field(default_factory=RetrievalFilters, description="通用过滤条件。")
    trace_id: str | None = Field(default=None, description="可选 trace 标识。")
    run_id: str | None = Field(default=None, description="可选 run 标识。")


class RetrievedDocument(BaseModel):
    """标准化文档实体。"""

    document_id: str = Field(..., min_length=1, description="文档唯一标识。")
    content: str = Field(..., description="文档正文内容。")
    title: str = Field(default="", description="文档标题。")
    source_uri: str = Field(default="", description="文档来源 URI。")
    metadata: dict[str, Any] = Field(default_factory=dict, description="通用元数据。")


class RetrievedCitation(BaseModel):
    """标准化引用条目。"""

    document_id: str = Field(..., min_length=1, description="引用对应的文档 ID。")
    title: str = Field(default="", description="引用标题。")
    source_uri: str = Field(default="", description="引用来源 URI。")
    snippet: str = Field(default="", description="引用摘要片段。")
    score: float | None = Field(default=None, description="可选检索得分。")


class RetrievalHit(BaseModel):
    """单条检索命中。"""

    document: RetrievedDocument = Field(..., description="命中文档。")
    score: float = Field(default=0.0, description="命中分数。")
    rank: int = Field(default=0, ge=0, description="最终排序名次，从 1 开始写入。")


class RetrievalResult(BaseModel):
    """统一检索结果。"""

    hits: list[RetrievalHit] = Field(default_factory=list, description="最终命中列表。")
    citations: list[RetrievedCitation] = Field(default_factory=list, description="标准化引用列表。")
    backend_name: str = Field(..., min_length=1, description="检索后端名称。")
    retriever_version: str = Field(..., min_length=1, description="检索器版本。")
    reranker_version: str = Field(..., min_length=1, description="重排器版本。")
    total_candidates: int = Field(default=0, ge=0, description="进入最终裁剪前的候选总数。")


class Retriever(Protocol):
    """检索器协议。"""

    backend_name: str
    retriever_version: str

    def retrieve(self, query: RetrievalQuery) -> list[RetrievalHit]:
        """执行检索。

        Args:
            query: 标准化检索请求。

        Returns:
            list[RetrievalHit]: 原始命中列表。
        """


class Reranker(Protocol):
    """重排器协议。"""

    reranker_name: str
    reranker_version: str

    def rerank(self, query: RetrievalQuery, hits: list[RetrievalHit]) -> list[RetrievalHit]:
        """执行重排。

        Args:
            query: 标准化检索请求。
            hits: 原始命中列表。

        Returns:
            list[RetrievalHit]: 重排后的命中列表。
        """


class EmbeddingProvider(Protocol):
    """向量嵌入提供者协议。"""

    provider_name: str
    provider_version: str

    def embed_query(self, text: str) -> list[float]:
        """对单条查询文本做向量化。

        Args:
            text: 查询文本。

        Returns:
            list[float]: 查询向量。
        """

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """对多条文档文本做向量化。

        Args:
            texts: 文本列表。

        Returns:
            list[list[float]]: 文档向量列表。
        """
