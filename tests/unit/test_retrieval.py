"""Retrieval 组件单元测试。"""

from __future__ import annotations

from agent_forge.components.context_engineering import ContextBudget, ContextEngineeringRuntime
from agent_forge.components.retrieval import (
    InMemoryRetriever,
    RetrievedDocument,
    RetrievalFilters,
    RetrievalHit,
    RetrievalQuery,
    RetrievalRuntime,
    build_citations_from_hits,
    to_context_citations,
)


class _ReverseScoreReranker:
    """测试用重排器：故意反转分数顺序。"""

    reranker_name = "reverse-score"
    reranker_version = "reverse-score-v1"

    def rerank(self, query: RetrievalQuery, hits: list[RetrievalHit]) -> list[RetrievalHit]:
        return sorted([item.model_copy(deep=True) for item in hits], key=lambda item: item.score)


def _documents() -> list[RetrievedDocument]:
    return [
        RetrievedDocument(
            document_id="doc-1",
            title="Python Tool Runtime",
            content="Python tool runtime supports timeout and retry policies.",
            source_uri="memory://doc-1",
            metadata={"topic": "tool"},
        ),
        RetrievedDocument(
            document_id="doc-2",
            title="Retrieval with Vectors",
            content="Vector retrieval needs embeddings and stable citations.",
            source_uri="memory://doc-2",
            metadata={"topic": "retrieval"},
        ),
        RetrievedDocument(
            document_id="doc-3",
            title="Agent Planning",
            content="Planning and reflection are engine responsibilities.",
            source_uri="memory://doc-3",
            metadata={"topic": "engine"},
        ),
    ]


def test_in_memory_retriever_should_return_sorted_hits() -> None:
    retriever = InMemoryRetriever(_documents())

    hits = retriever.retrieve(RetrievalQuery(query_text="retrieval embeddings", top_k=3))

    assert len(hits) >= 1
    assert hits[0].document.document_id == "doc-2"
    assert hits[0].score >= hits[-1].score


def test_retrieval_runtime_should_build_result_with_versions_and_citations() -> None:
    runtime = RetrievalRuntime(InMemoryRetriever(_documents()))

    result = runtime.search(RetrievalQuery(query_text="tool runtime retry", top_k=2))

    assert result.backend_name == "inmemory"
    assert result.retriever_version == "inmemory-v1"
    assert result.reranker_version == "none"
    assert result.total_candidates >= len(result.hits)
    assert len(result.citations) == len(result.hits)


def test_retrieval_runtime_should_apply_reranker_and_rewrite_rank() -> None:
    runtime = RetrievalRuntime(InMemoryRetriever(_documents()), reranker=_ReverseScoreReranker())

    result = runtime.search(RetrievalQuery(query_text="retrieval vector embeddings", top_k=2))

    assert len(result.hits) >= 1
    assert result.reranker_version == "reverse-score-v1"
    assert [item.rank for item in result.hits] == list(range(1, len(result.hits) + 1))


def test_retriever_should_apply_filters() -> None:
    retriever = InMemoryRetriever(_documents())

    hits = retriever.retrieve(
        RetrievalQuery(
            query_text="runtime retry",
            filters=RetrievalFilters(metadata_equals={"topic": "tool"}),
        )
    )

    assert len(hits) == 1
    assert hits[0].document.document_id == "doc-1"


def test_retrieval_runtime_should_return_empty_result_for_no_hit() -> None:
    runtime = RetrievalRuntime(InMemoryRetriever(_documents()))

    result = runtime.search(RetrievalQuery(query_text="nonexistent phrase", top_k=3))

    assert result.hits == []
    assert result.citations == []
    assert result.total_candidates == 0


def test_build_citations_and_context_bridge_should_work() -> None:
    runtime = RetrievalRuntime(InMemoryRetriever(_documents()))
    result = runtime.search(RetrievalQuery(query_text="vector embeddings", top_k=1))
    citations = build_citations_from_hits(result.hits)
    context_citations = to_context_citations(citations)
    context_runtime = ContextEngineeringRuntime()

    bundle = context_runtime.build_bundle(
        system_prompt="system",
        messages=[],
        citations=context_citations,
        tools=[],
        budget=ContextBudget(max_input_tokens=300, reserved_output_tokens=50),
    )

    assert len(context_citations) == 1
    assert len(bundle.citations) == 1
    assert any("回答时请使用以下引用：" in item.content for item in bundle.messages)


def test_retrieval_runtime_should_apply_min_score_and_top_k() -> None:
    runtime = RetrievalRuntime(InMemoryRetriever(_documents()))

    result = runtime.search(RetrievalQuery(query_text="retrieval embeddings", top_k=1, min_score=0.5))

    assert len(result.hits) == 1
    assert result.hits[0].score >= 0.5
