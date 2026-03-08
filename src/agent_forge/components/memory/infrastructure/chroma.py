"""Memory 的 Chroma 向量存储实现。"""

from __future__ import annotations

import importlib
from typing import Any

from agent_forge.components.memory.domain import MemoryReadQuery, MemoryRecord, MemoryVectorHit
from agent_forge.components.retrieval import EmbeddingProvider


class ChromaMemoryVectorStore:
    """基于 Chroma 的向量记忆存储。"""

    backend_name = "chroma_memory"
    backend_version = "chroma-memory-v1"

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        collection: Any | None = None,
        client: Any | None = None,
        collection_name: str = "agent_forge_memory",
    ) -> None:
        """初始化 ChromaMemoryVectorStore。

        Args:
            embedding_provider: 向量提供器。
            collection: 可选已存在 collection。
            client: 可选 Chroma client。
            collection_name: collection 名称。

        Returns:
            None.

        Raises:
            RuntimeError: 当未安装 chromadb 且没有注入 collection/client 时抛出。
        """

        self._embedding_provider = embedding_provider
        self._collection = self._resolve_collection(collection=collection, client=client, collection_name=collection_name)

    def upsert(self, records: list[MemoryRecord]) -> int:
        """写入向量记忆。

        Args:
            records: 待写入记录。

        Returns:
            int: 实际写入数量。
        """

        if not records:
            return 0
        ids = [record.memory_id for record in records]
        texts = [_record_to_vector_text(record) for record in records]
        metadatas = [_record_to_metadata(record) for record in records]
        embeddings = self._embedding_provider.embed_documents(texts)
        if hasattr(self._collection, "upsert"):
            self._collection.upsert(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
        else:
            self._collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
        return len(records)

    def query(self, query: MemoryReadQuery) -> list[MemoryVectorHit]:
        """执行向量查询。

        Args:
            query: 查询请求。

        Returns:
            list[MemoryVectorHit]: 命中结果。
        """

        if not query.query_text:
            return []
        query_vector = self._embedding_provider.embed_query(query.query_text)
        query_kwargs: dict[str, Any] = {
            "query_embeddings": [query_vector],
            "n_results": query.top_k,
            "include": ["metadatas", "distances"],
        }
        where = _build_where(query)
        if where:
            query_kwargs["where"] = where
        result = self._collection.query(**query_kwargs)
        return _hits_from_query_result(result)

    def invalidate(
        self,
        *,
        tenant_id: str,
        user_id: str,
        session_id: str | None,
        memory_ids: list[str],
    ) -> int:
        """失效向量记录。

        Args:
            tenant_id: 租户 ID。
            user_id: 用户 ID。
            session_id: 会话 ID。
            memory_ids: 待失效记忆 ID。

        Returns:
            int: 实际失效数量。
        """

        if not memory_ids:
            return 0
        if hasattr(self._collection, "delete") and not hasattr(self._collection, "get"):
            self._collection.delete(ids=memory_ids)
            return len(memory_ids)
        if not hasattr(self._collection, "update") or not hasattr(self._collection, "get"):
            raise RuntimeError(
                "ChromaMemoryVectorStore.invalidate 需要 collection.get + collection.update，"
                "或者至少支持 collection.delete。"
            )
        existing = self._load_existing_metadatas(memory_ids)
        payload = []
        for index, memory_id in enumerate(memory_ids):
            current = existing[index] if index < len(existing) else {}
            merged = dict(current)
            merged.setdefault("memory_id", memory_id)
            merged.setdefault("tenant_id", tenant_id)
            merged.setdefault("user_id", user_id)
            merged.setdefault("session_id", session_id or "")
            merged["invalidated"] = True
            payload.append(merged)
        self._collection.update(ids=memory_ids, metadatas=payload)
        return len(memory_ids)

    def _resolve_collection(self, *, collection: Any | None, client: Any | None, collection_name: str) -> Any:
        """解析 collection。

        Args:
            collection: 可选 collection。
            client: 可选 client。
            collection_name: collection 名。

        Returns:
            Any: 可用 collection。

        Raises:
            RuntimeError: 当缺少 chromadb 依赖时抛出。
        """

        if collection is not None:
            return collection
        if client is not None:
            return client.get_or_create_collection(name=collection_name)
        try:
            chromadb = importlib.import_module("chromadb")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "使用 ChromaMemoryVectorStore 需要安装 `agent-forge[memory-chroma]`，"
                "或手动注入可用的 collection/client。"
            ) from exc
        return chromadb.EphemeralClient().get_or_create_collection(name=collection_name)

    def _load_existing_metadatas(self, memory_ids: list[str]) -> list[dict[str, Any]]:
        """批量读取已有 metadata，供 invalidate 时做安全合并。

        Args:
            memory_ids: 需要查询的记忆 ID 列表。

        Returns:
            list[dict[str, Any]]: 与 memory_ids 顺序对齐的 metadata 列表。
        """

        if not hasattr(self._collection, "get"):
            return [{} for _ in memory_ids]
        result = self._collection.get(ids=memory_ids, include=["metadatas"])
        metadatas = _first_or_empty(result.get("metadatas"))
        lookup: dict[str, dict[str, Any]] = {}
        ids = _first_or_empty(result.get("ids"))
        for index, memory_id in enumerate(ids):
            metadata = metadatas[index] if index < len(metadatas) and isinstance(metadatas[index], dict) else {}
            lookup[str(memory_id)] = dict(metadata)
        return [lookup.get(memory_id, {}) for memory_id in memory_ids]


def _record_to_vector_text(record: MemoryRecord) -> str:
    """把记忆记录转换为向量文本。

    Args:
        record: 记忆记录。

    Returns:
        str: 向量化文本。
    """

    summary = record.summary.strip()
    if summary:
        return f"{summary}\n{record.content}"
    return record.content


def _record_to_metadata(record: MemoryRecord) -> dict[str, str | int | float | bool]:
    """转换向量 metadata。

    Args:
        record: 记忆记录。

    Returns:
        dict[str, str | int | float | bool]: Chroma 可接受的 metadata。

    Raises:
        ValueError: 当 metadata 含不支持类型时抛出。
    """

    metadata: dict[str, str | int | float | bool] = {
        "memory_id": record.memory_id,
        "record_key": record.record_key,
        "tenant_id": record.tenant_id,
        "user_id": record.user_id,
        "session_id": record.session_id or "",
        "scope": record.scope,
        "category": record.category,
        "invalidated": record.invalidated,
        "created_at": record.created_at,
    }
    for key, value in record.metadata.items():
        if value is None:
            continue
        metadata[key] = _coerce_metadata_value(key, value)
    return metadata


def _coerce_metadata_value(key: str, value: Any) -> str | int | float | bool:
    """收口 metadata 类型。

    Args:
        key: 字段名。
        value: 字段值。

    Returns:
        str | int | float | bool: Chroma 可接受类型。

    Raises:
        ValueError: 当值类型不受支持时抛出。
    """

    if isinstance(value, bool):
        return value
    if isinstance(value, (str, int, float)):
        return value
    raise ValueError(f"ChromaMemoryVectorStore 不支持 metadata 字段 `{key}` 的 `{type(value).__name__}` 类型")


def _build_where(query: MemoryReadQuery) -> dict[str, Any] | None:
    """构造 Chroma where 条件。

    Args:
        query: 查询请求。

    Returns:
        dict[str, Any] | None: where 条件。
    """

    conditions: list[dict[str, Any]] = [
        {"tenant_id": query.tenant_id},
        {"user_id": query.user_id},
    ]
    if query.scope is not None:
        conditions.append({"scope": query.scope})
    if query.scope == "session":
        conditions.append({"session_id": query.session_id or ""})
    if query.categories:
        conditions.append({"category": {"$in": query.categories}})
    if not query.include_invalidated:
        conditions.append({"invalidated": False})
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def _hits_from_query_result(result: dict[str, Any]) -> list[MemoryVectorHit]:
    """把 Chroma 查询结果转成 MemoryVectorHit。

    Args:
        result: Chroma 原始结果。

    Returns:
        list[MemoryVectorHit]: 命中结果。
    """

    ids = _first_or_empty(result.get("ids"))
    metadatas = _first_or_empty(result.get("metadatas"))
    distances = _first_or_empty(result.get("distances"))
    hits: list[MemoryVectorHit] = []
    for index, memory_id in enumerate(ids):
        metadata = metadatas[index] if index < len(metadatas) and isinstance(metadatas[index], dict) else {}
        distance = distances[index] if index < len(distances) else None
        hits.append(
            MemoryVectorHit(
                memory_id=str(metadata.get("memory_id") or memory_id),
                score=_distance_to_score(distance),
                metadata=dict(metadata),
            )
        )
    hits.sort(key=lambda item: (-item.score, item.memory_id))
    return hits


def _distance_to_score(distance: Any) -> float:
    """把 distance 转为 score。

    Args:
        distance: 原始 distance。

    Returns:
        float: 相似度分数。
    """

    if not isinstance(distance, (int, float)):
        return 0.0
    if distance <= 0:
        return 1.0
    return 1.0 / (1.0 + float(distance))


def _first_or_empty(payload: Any) -> list[Any]:
    """从 Chroma 返回值中取第一层结果。

    Args:
        payload: 原始 payload。

    Returns:
        list[Any]: 第一层结果。
    """

    if not isinstance(payload, list) or not payload:
        return []
    head = payload[0]
    return head if isinstance(head, list) else payload
