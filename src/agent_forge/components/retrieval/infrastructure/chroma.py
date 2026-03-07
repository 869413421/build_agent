"""Chroma 向量检索适配器。"""

from __future__ import annotations

import importlib
from typing import Any

from agent_forge.components.retrieval.domain import (
    EmbeddingProvider,
    RetrievedDocument,
    RetrievalFilters,
    RetrievalHit,
    RetrievalQuery,
)
from agent_forge.components.retrieval.infrastructure.helpers import matches_filters


class ChromaRetriever:
    """基于 Chroma 的真实向量检索适配器。"""

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        collection: Any | None = None,
        client: Any | None = None,
        collection_name: str = "agent_forge_retrieval",
        backend_name: str = "chroma",
        retriever_version: str = "chroma-v1",
    ) -> None:
        """初始化 Chroma 检索器。

        Args:
            embedding_provider: 向量嵌入提供者。
            collection: 已存在的 Chroma collection，可用于测试或外部注入。
            client: 可选 Chroma client。
            collection_name: collection 名称。
            backend_name: 后端名称。
            retriever_version: 检索器版本。

        Returns:
            None.

        Raises:
            RuntimeError: 当未注入 collection/client 且环境未安装 chromadb。
        """

        self.backend_name = backend_name
        self.retriever_version = retriever_version
        self._embedding_provider = embedding_provider
        self._collection = self._resolve_collection(collection=collection, client=client, collection_name=collection_name)

    def upsert_documents(self, documents: list[RetrievedDocument]) -> None:
        """写入或更新文档到 Chroma collection。

        Args:
            documents: 待写入文档列表。

        Returns:
            None.
        """

        if not documents:
            return

        # 1. 先统一把框架标准文档转换成 Chroma 需要的 ids/documents/metadatas/embeddings。
        ids = [item.document_id for item in documents]
        texts = [item.content for item in documents]
        metadatas = [_document_to_metadata(item) for item in documents]
        embeddings = self._embedding_provider.embed_documents(texts)

        # 2. 优先使用 upsert；若底层 collection 不支持，则退回 add，保证适配层兼容更多版本。
        if hasattr(self._collection, "upsert"):
            self._collection.upsert(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
            return
        self._collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)

    def retrieve(self, query: RetrievalQuery) -> list[RetrievalHit]:
        """执行 Chroma 查询并标准化命中结果。

        Args:
            query: 标准化检索请求。

        Returns:
            list[RetrievalHit]: 标准化命中列表。
        """

        # 1. 先把查询文本向量化，再执行 Chroma 原生查询。
        query_vector = self._embedding_provider.embed_query(query.query_text)
        query_kwargs: dict[str, Any] = {
            "query_embeddings": [query_vector],
            "n_results": max(query.top_k, query.top_k * 3),
            "include": ["documents", "metadatas", "distances"],
        }
        where = _build_where(query.filters)
        if where:
            query_kwargs["where"] = where
        result = self._collection.query(
            **query_kwargs,
        )

        # 2. 把 Chroma 的结构化返回映射回框架标准 hit，并在适配层执行通用 filters。
        hits = _hits_from_chroma_result(result)
        filtered_hits = [item for item in hits if matches_filters(item.document, query.filters)]

        # 3. 最终按 score 倒序稳定排序，把距离语义统一成“分数越高越好”。
        filtered_hits.sort(key=lambda item: (-item.score, item.document.document_id))
        return filtered_hits

    def _resolve_collection(self, *, collection: Any | None, client: Any | None, collection_name: str) -> Any:
        """解析 collection 来源。

        Args:
            collection: 外部直接注入的 collection。
            client: 外部注入的 client。
            collection_name: collection 名称。

        Returns:
            Any: 可用的 collection 对象。

        Raises:
            RuntimeError: 当 chromadb 不可用且没有外部注入 collection/client。
        """

        if collection is not None:
            return collection
        if client is not None:
            return client.get_or_create_collection(name=collection_name)
        try:
            chromadb = importlib.import_module("chromadb")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "未安装 chromadb，无法初始化 ChromaRetriever。请安装可选依赖 `agent-forge[retrieval-chroma]`，或显式注入 collection/client。"
            ) from exc
        return chromadb.EphemeralClient().get_or_create_collection(name=collection_name)


def _document_to_metadata(document: RetrievedDocument) -> dict[str, Any]:
    """转换文档元数据为 Chroma 可存储结构。

    Args:
        document: 标准化文档。

    Returns:
        dict[str, Any]: 可写入 Chroma 的元数据。
    """

    metadata: dict[str, Any] = {}
    for key, value in document.metadata.items():
        if value is None:
            continue
        metadata[key] = _coerce_metadata_value(key, value)
    metadata["document_id"] = document.document_id
    metadata["title"] = document.title
    metadata["source_uri"] = document.source_uri
    return metadata


def _coerce_metadata_value(key: str, value: Any) -> str | int | float | bool:
    """把 metadata 值收口到 Chroma 可接受的标量类型。

    Args:
        key: 元数据键名。
        value: 原始元数据值。

    Returns:
        str | int | float | bool: 可写入 Chroma 的标量值。

    Raises:
        ValueError: 当元数据值不是 Chroma 可接受的标量类型时抛出。
    """

    if isinstance(value, bool):
        return value
    if isinstance(value, (str, int, float)):
        return value
    raise ValueError(
        f"ChromaRetriever 仅支持标量 metadata，字段 `{key}` 的值类型为 `{type(value).__name__}`。"
    )


def _build_where(filters: RetrievalFilters) -> dict[str, Any] | None:
    """把通用过滤条件映射为 Chroma where 查询。

    Args:
        filters: 通用过滤条件。

    Returns:
        dict[str, Any] | None: Chroma where 条件；若无条件则返回 None。
    """

    conditions: list[dict[str, Any]] = []
    if filters.document_ids:
        conditions.append(_build_scalar_or_in_condition("document_id", filters.document_ids))
    if filters.source_uris:
        conditions.append(_build_scalar_or_in_condition("source_uri", filters.source_uris))
    for key, value in filters.metadata_equals.items():
        if value is None:
            continue
        conditions.append({key: _coerce_metadata_value(key, value)})
    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def _build_scalar_or_in_condition(field_name: str, values: list[str]) -> dict[str, Any]:
    """为单值或多值过滤构造 Chroma where 子句。

    Args:
        field_name: 字段名。
        values: 候选值列表。

    Returns:
        dict[str, Any]: where 子句。
    """

    if len(values) == 1:
        return {field_name: values[0]}
    return {field_name: {"$in": values}}


def _hits_from_chroma_result(result: dict[str, Any]) -> list[RetrievalHit]:
    """把 Chroma query 返回结果映射为标准命中列表。

    Args:
        result: Chroma query 原始结果。

    Returns:
        list[RetrievalHit]: 标准化命中列表。
    """

    ids = _first_or_empty(result.get("ids"))
    documents = _first_or_empty(result.get("documents"))
    metadatas = _first_or_empty(result.get("metadatas"))
    distances = _first_or_empty(result.get("distances"))
    hits: list[RetrievalHit] = []

    for index, document_id in enumerate(ids):
        metadata = metadatas[index] if index < len(metadatas) and isinstance(metadatas[index], dict) else {}
        content = documents[index] if index < len(documents) else ""
        distance = distances[index] if index < len(distances) else None
        score = _distance_to_score(distance)
        hits.append(
            RetrievalHit(
                document=RetrievedDocument(
                    document_id=str(metadata.get("document_id") or document_id),
                    content=str(content),
                    title=str(metadata.get("title", "")),
                    source_uri=str(metadata.get("source_uri", "")),
                    metadata={key: value for key, value in metadata.items() if key not in {"document_id", "title", "source_uri"}},
                ),
                score=score,
            )
        )
    return hits


def _distance_to_score(distance: Any) -> float:
    """把距离值归一化成分数。

    Args:
        distance: 原始距离值。

    Returns:
        float: 归一化后的分数，越大越好。
    """

    if not isinstance(distance, (int, float)):
        return 0.0
    if distance <= 0:
        return 1.0
    return 1.0 / (1.0 + float(distance))


def _first_or_empty(payload: Any) -> list[Any]:
    """兼容 Chroma 的双层列表返回结构。

    Args:
        payload: 原始字段值。

    Returns:
        list[Any]: 首层结果列表。
    """

    if not isinstance(payload, list) or not payload:
        return []
    head = payload[0]
    return head if isinstance(head, list) else payload
