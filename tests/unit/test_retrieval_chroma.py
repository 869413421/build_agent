"""ChromaRetriever 单元测试。"""

from __future__ import annotations

import importlib

import pytest

from agent_forge.components.retrieval import ChromaRetriever, RetrievedDocument, RetrievalQuery


class _FakeEmbeddingProvider:
    """测试用嵌入提供者。"""

    provider_name = "fake-embedding"
    provider_version = "fake-embedding-v1"

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text)), 1.0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 1.0] for text in texts]


class _FakeCollection:
    """测试用 Chroma collection。"""

    def __init__(self) -> None:
        self.upsert_payload: dict[str, object] | None = None
        self.query_payload: dict[str, object] | None = None

    def upsert(self, **kwargs: object) -> None:
        self.upsert_payload = kwargs

    def query(self, **kwargs: object) -> dict[str, object]:
        self.query_payload = kwargs
        return {
            "ids": [["doc-1", "doc-2"]],
            "documents": [["vector search document", "other content"]],
            "metadatas": [[
                {"document_id": "doc-1", "title": "Doc 1", "source_uri": "memory://doc-1", "topic": "retrieval"},
                {"document_id": "doc-2", "title": "Doc 2", "source_uri": "memory://doc-2", "topic": "other"},
            ]],
            "distances": [[0.1, 0.9]],
        }


def test_chroma_retriever_should_upsert_documents_using_embedding_provider() -> None:
    collection = _FakeCollection()
    retriever = ChromaRetriever(collection=collection, embedding_provider=_FakeEmbeddingProvider())

    retriever.upsert_documents(
        [
            RetrievedDocument(
                document_id="doc-1",
                title="Doc 1",
                content="vector search document",
                source_uri="memory://doc-1",
                metadata={"topic": "retrieval"},
            )
        ]
    )

    assert collection.upsert_payload is not None
    assert collection.upsert_payload["ids"] == ["doc-1"]
    assert collection.upsert_payload["embeddings"] == [[22.0, 1.0]]


def test_chroma_retriever_should_query_and_standardize_results() -> None:
    collection = _FakeCollection()
    retriever = ChromaRetriever(collection=collection, embedding_provider=_FakeEmbeddingProvider())

    hits = retriever.retrieve(RetrievalQuery(query_text="vector search", top_k=2))

    assert len(hits) == 2
    assert hits[0].document.document_id == "doc-1"
    assert hits[0].score > hits[1].score
    assert collection.query_payload is not None
    assert "where" not in collection.query_payload


def test_chroma_retriever_should_translate_filters_into_where_clause() -> None:
    collection = _FakeCollection()
    retriever = ChromaRetriever(collection=collection, embedding_provider=_FakeEmbeddingProvider())

    retriever.retrieve(
        RetrievalQuery(
            query_text="vector search",
            top_k=2,
            filters={
                "document_ids": ["doc-1"],
                "metadata_equals": {"topic": "retrieval"},
            },
        )
    )

    assert collection.query_payload is not None
    where = collection.query_payload.get("where")
    assert isinstance(where, dict)
    assert "$and" in where


def test_chroma_retriever_should_reject_unsupported_metadata_type() -> None:
    collection = _FakeCollection()
    retriever = ChromaRetriever(collection=collection, embedding_provider=_FakeEmbeddingProvider())

    with pytest.raises(ValueError) as excinfo:
        retriever.upsert_documents(
            [
                RetrievedDocument(
                    document_id="doc-1",
                    title="Doc 1",
                    content="vector search document",
                    source_uri="memory://doc-1",
                    metadata={"tags": ["retrieval", "vector"]},
                )
            ]
        )

    assert "仅支持标量 metadata" in str(excinfo.value)


def test_chroma_retriever_should_raise_clear_error_when_dependency_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import_module = importlib.import_module

    def _fake_import_module(name: str):
        if name == "chromadb":
            raise ModuleNotFoundError("chromadb")
        return original_import_module(name)

    monkeypatch.setattr(importlib, "import_module", _fake_import_module)

    with pytest.raises(RuntimeError) as excinfo:
        ChromaRetriever(embedding_provider=_FakeEmbeddingProvider())

    assert "retrieval-chroma" in str(excinfo.value)
