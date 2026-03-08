"""Memory Chroma 向量层测试。"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

from agent_forge.components.memory import ChromaMemoryVectorStore, MemoryReadQuery, MemoryRecord, MemorySource


class _FakeEmbeddingProvider:
    provider_name = "fake-embedding"
    provider_version = "fake-embedding-v1"

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text)), 1.0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(item)), 1.0] for item in texts]


class _FakeCollection:
    def __init__(self) -> None:
        self.upsert_payload: dict[str, Any] | None = None
        self.query_payload: dict[str, Any] | None = None
        self.update_payload: dict[str, Any] | None = None
        self.get_payload: dict[str, Any] | None = None
        self.seed_metadata: dict[str, Any] = {
            "memory_id": "mem_1",
            "tenant_id": "tenant_a",
            "user_id": "user_a",
            "session_id": "",
            "scope": "long_term",
            "category": "preference",
            "record_key": "pref_format",
            "invalidated": False,
        }

    def upsert(self, **kwargs: Any) -> None:
        self.upsert_payload = kwargs

    def query(self, **kwargs: Any) -> dict[str, Any]:
        self.query_payload = kwargs
        return {
            "ids": [["mem_1"]],
            "metadatas": [[{"memory_id": "mem_1", "tenant_id": "tenant_a", "user_id": "user_a", "scope": "long_term"}]],
            "distances": [[0.1]],
        }

    def get(self, **kwargs: Any) -> dict[str, Any]:
        self.get_payload = kwargs
        return {
            "ids": [["mem_1"]],
            "metadatas": [[dict(self.seed_metadata)]],
        }

    def update(self, **kwargs: Any) -> None:
        self.update_payload = kwargs


class _DeleteOnlyCollection:
    def __init__(self) -> None:
        self.delete_payload: dict[str, Any] | None = None

    def delete(self, **kwargs: Any) -> None:
        self.delete_payload = kwargs


class _UpdateOnlyCollection:
    def __init__(self) -> None:
        self.update_payload: dict[str, Any] | None = None

    def update(self, **kwargs: Any) -> None:
        self.update_payload = kwargs


def _record(**kwargs: Any) -> MemoryRecord:
    metadata = kwargs.pop("metadata", {})
    return MemoryRecord(
        memory_id="mem_1",
        record_key="pref_format",
        scope="long_term",
        tenant_id="tenant_a",
        user_id="user_a",
        session_id=None,
        category="preference",
        content="用户偏好条列式输出。",
        summary="偏好条列式",
        source=MemorySource(source_type="agent_message", source_excerpt="条列式"),
        metadata=metadata,
        **kwargs,
    )


def test_memory_chroma_store_should_upsert_records() -> None:
    collection = _FakeCollection()
    store = ChromaMemoryVectorStore(collection=collection, embedding_provider=_FakeEmbeddingProvider())

    count = store.upsert([_record()])

    assert count == 1
    assert collection.upsert_payload is not None
    assert collection.upsert_payload["ids"] == ["mem_1"]
    assert collection.upsert_payload["embeddings"] == [[16.0, 1.0]]


def test_memory_chroma_store_should_translate_query_into_where_clause() -> None:
    collection = _FakeCollection()
    store = ChromaMemoryVectorStore(collection=collection, embedding_provider=_FakeEmbeddingProvider())

    hits = store.query(
        MemoryReadQuery(
            tenant_id="tenant_a",
            user_id="user_a",
            session_id="session_a",
            scope="long_term",
            categories=["preference"],
            top_k=3,
            query_text="输出偏好",
        )
    )

    assert len(hits) == 1
    assert collection.query_payload is not None
    where = collection.query_payload.get("where")
    assert isinstance(where, dict)
    assert "$and" in where


def test_memory_chroma_store_should_invalidate_records() -> None:
    collection = _FakeCollection()
    store = ChromaMemoryVectorStore(collection=collection, embedding_provider=_FakeEmbeddingProvider())

    count = store.invalidate(
        tenant_id="tenant_a",
        user_id="user_a",
        session_id="session_a",
        memory_ids=["mem_1"],
    )

    assert count == 1
    assert collection.update_payload is not None
    assert collection.update_payload["ids"] == ["mem_1"]


def test_memory_chroma_store_should_reject_unsupported_metadata_type() -> None:
    collection = _FakeCollection()
    store = ChromaMemoryVectorStore(collection=collection, embedding_provider=_FakeEmbeddingProvider())

    with pytest.raises(ValueError):
        store.upsert([_record(metadata={"tags": ["a", "b"]})])


def test_memory_chroma_store_should_raise_clear_error_when_dependency_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import_module = importlib.import_module

    def _fake_import(name: str):
        if name == "chromadb":
            raise ModuleNotFoundError("chromadb")
        return original_import_module(name)

    monkeypatch.setattr(importlib, "import_module", _fake_import)

    with pytest.raises(RuntimeError) as excinfo:
        ChromaMemoryVectorStore(embedding_provider=_FakeEmbeddingProvider())

    assert "memory-chroma" in str(excinfo.value)


def test_memory_chroma_store_should_preserve_existing_metadata_when_invalidating() -> None:
    collection = _FakeCollection()
    store = ChromaMemoryVectorStore(collection=collection, embedding_provider=_FakeEmbeddingProvider())

    count = store.invalidate(
        tenant_id="tenant_a",
        user_id="user_a",
        session_id=None,
        memory_ids=["mem_1"],
    )

    assert count == 1
    assert collection.get_payload is not None
    assert collection.update_payload is not None
    metadata = collection.update_payload["metadatas"][0]
    assert metadata["memory_id"] == "mem_1"
    assert metadata["scope"] == "long_term"
    assert metadata["category"] == "preference"
    assert metadata["record_key"] == "pref_format"
    assert metadata["invalidated"] is True


def test_memory_chroma_store_should_fallback_to_delete_when_get_is_unavailable() -> None:
    collection = _DeleteOnlyCollection()
    store = ChromaMemoryVectorStore(collection=collection, embedding_provider=_FakeEmbeddingProvider())

    count = store.invalidate(tenant_id="tenant_a", user_id="user_a", session_id=None, memory_ids=["mem_1"])

    assert count == 1
    assert collection.delete_payload is not None
    assert collection.delete_payload["ids"] == ["mem_1"]


def test_memory_chroma_store_should_raise_when_invalidate_cannot_merge_or_delete() -> None:
    collection = _UpdateOnlyCollection()
    store = ChromaMemoryVectorStore(collection=collection, embedding_provider=_FakeEmbeddingProvider())

    with pytest.raises(RuntimeError):
        store.invalidate(tenant_id="tenant_a", user_id="user_a", session_id=None, memory_ids=["mem_1"])
