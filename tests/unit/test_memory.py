"""Memory 主流程测试。"""

from __future__ import annotations

from typing import Any

import pytest

from agent_forge.components.memory import (
    MemoryExtractor,
    MemoryReadQuery,
    MemoryRuntime,
    MemoryVectorHit,
    MemoryWriteRequest,
    InMemoryLongTermMemoryStore,
    InMemorySessionMemoryStore,
)
from agent_forge.components.model_runtime import ModelRequest, ModelResponse, ModelStats
from agent_forge.components.protocol import AgentMessage, AgentState, FinalAnswer, ToolResult


class _FakeVectorStore:
    """æ ¹æ® scope è¿ååºå®å½ä¸­çååéå­å¨ã"""

    backend_name = "fake-memory-vector"
    backend_version = "fake-memory-vector-v1"

    def __init__(self, hits_by_scope: dict[str, list[MemoryVectorHit]] | None = None, default_hits: list[MemoryVectorHit] | None = None) -> None:
        self.hits_by_scope = hits_by_scope or {}
        self.default_hits = default_hits or []
        self.queries: list[MemoryReadQuery] = []

    def upsert(self, records: list[object]) -> int:
        return len(records)

    def query(self, query: MemoryReadQuery) -> list[MemoryVectorHit]:
        self.queries.append(query)
        if query.scope is None:
            return list(self.default_hits)
        return list(self.hits_by_scope.get(query.scope, self.default_hits))

    def invalidate(self, **kwargs: Any) -> int:
        return len(kwargs.get("memory_ids", []))


class _FakeModelRuntime:
    """返回固定抽取结果的假模型运行时。"""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        self.requests.append(request)
        return ModelResponse(
            content='{"items": []}',
            parsed_output=self.payload,
            stats=ModelStats(total_tokens=16),
        )


def _build_runtime(payload: dict[str, Any]) -> tuple[MemoryRuntime, _FakeModelRuntime]:
    fake_runtime = _FakeModelRuntime(payload)
    runtime = MemoryRuntime(
        extractor=MemoryExtractor(model_runtime=fake_runtime),
        session_store=InMemorySessionMemoryStore(),
        long_term_store=InMemoryLongTermMemoryStore(),
    )
    return runtime, fake_runtime


def test_memory_should_write_finish_summary_into_both_scopes() -> None:
    runtime, fake_runtime = _build_runtime(
        {
            "items": [
                {
                    "scope": "session",
                    "category": "summary",
                    "record_key": "session_summary",
                    "content": "本轮完成了董事会摘要整理。",
                    "summary": "董事会摘要整理",
                    "source_excerpt": "董事会摘要",
                },
                {
                    "scope": "long_term",
                    "category": "summary",
                    "record_key": "long_term_summary",
                    "content": "用户长期关注董事会汇报质量。",
                    "summary": "长期关注董事会汇报",
                    "source_excerpt": "关注董事会汇报",
                },
            ]
        }
    )

    result = runtime.write(
        MemoryWriteRequest(
            tenant_id="tenant_a",
            user_id="user_a",
            session_id="session_a",
            trigger="finish",
            final_answer=FinalAnswer(status="success", summary="完成", output={"ok": True}),
        )
    )

    assert len(result.records) == 2
    assert result.extracted_count == 2
    assert fake_runtime.requests[0].response_schema is not None


def test_memory_should_extract_fact_memories_from_state() -> None:
    runtime, _ = _build_runtime(
        {
            "items": [
                {
                    "scope": "long_term",
                    "category": "fact",
                    "record_key": "company_stage",
                    "content": "客户公司正在筹备 A 轮融资。",
                    "summary": "公司筹备 A 轮融资",
                    "source_excerpt": "筹备 A 轮融资",
                }
            ]
        }
    )
    state = AgentState(session_id="session_a")
    state.messages.append(AgentMessage(role="user", content="我们正在准备 A 轮融资材料。"))
    state.tool_results.append(ToolResult(tool_call_id="tc1", status="ok", output={"finance_stage": "Series A prep"}))

    result = runtime.write(
        MemoryWriteRequest(
            tenant_id="tenant_a",
            user_id="user_a",
            session_id="session_a",
            trigger="fact",
            agent_state=state,
        )
    )

    assert len(result.records) == 1
    assert result.records[0].category == "fact"
    assert result.records[0].scope == "long_term"


def test_memory_should_extract_preference_memories() -> None:
    runtime, _ = _build_runtime(
        {
            "items": [
                {
                    "scope": "long_term",
                    "category": "preference",
                    "record_key": "pref_language",
                    "content": "用户偏好中文输出。",
                    "summary": "偏好中文输出",
                    "source_excerpt": "请默认用中文",
                }
            ]
        }
    )

    result = runtime.write(
        MemoryWriteRequest(
            tenant_id="tenant_a",
            user_id="user_a",
            session_id="session_a",
            trigger="preference",
            messages=[AgentMessage(role="user", content="之后请默认用中文回答。")],
        )
    )

    assert len(result.records) == 1
    assert result.records[0].category == "preference"


def test_memory_should_apply_last_write_wins_for_same_record_key() -> None:
    runtime, _ = _build_runtime(
        {
            "items": [
                {
                    "scope": "long_term",
                    "category": "preference",
                    "record_key": "pref_format",
                    "content": "用户偏好条列式输出。",
                    "summary": "偏好条列式",
                    "source_excerpt": "条列式",
                }
            ]
        }
    )
    first = runtime.write(
        MemoryWriteRequest(
            tenant_id="tenant_a",
            user_id="user_a",
            session_id="session_a",
            trigger="preference",
        )
    )
    runtime._extractor = MemoryExtractor(  # type: ignore[attr-defined]
        model_runtime=_FakeModelRuntime(
            {
                "items": [
                    {
                        "scope": "long_term",
                        "category": "preference",
                        "record_key": "pref_format",
                        "content": "用户偏好表格输出。",
                        "summary": "偏好表格输出",
                        "source_excerpt": "表格输出",
                    }
                ]
            }
        )
    )
    second = runtime.write(
        MemoryWriteRequest(
            tenant_id="tenant_a",
            user_id="user_a",
            session_id="session_a",
            trigger="preference",
        )
    )

    assert first.records[0].memory_id == second.records[0].memory_id
    assert second.records[0].version == 2
    assert second.records[0].summary == "偏好表格输出"


def test_memory_should_isolate_reads_by_tenant_user_and_session() -> None:
    runtime, _ = _build_runtime(
        {
            "items": [
                {
                    "scope": "session",
                    "category": "summary",
                    "record_key": "session_summary",
                    "content": "会话摘要 A",
                    "summary": "摘要 A",
                    "source_excerpt": "摘要 A",
                }
            ]
        }
    )
    runtime.write(MemoryWriteRequest(tenant_id="tenant_a", user_id="user_a", session_id="session_a", trigger="finish"))
    runtime.write(MemoryWriteRequest(tenant_id="tenant_a", user_id="user_a", session_id="session_b", trigger="finish"))

    read_a = runtime.read(
        MemoryReadQuery(
            tenant_id="tenant_a",
            user_id="user_a",
            session_id="session_a",
            scope="session",
            top_k=5,
        )
    )

    assert len(read_a.records) == 1
    assert read_a.records[0].session_id == "session_a"


def test_memory_should_invalidate_records() -> None:
    runtime, _ = _build_runtime(
        {
            "items": [
                {
                    "scope": "long_term",
                    "category": "fact",
                    "record_key": "customer_plan",
                    "content": "客户计划下月上线。",
                    "summary": "客户下月上线",
                    "source_excerpt": "下月上线",
                }
            ]
        }
    )
    result = runtime.write(
        MemoryWriteRequest(
            tenant_id="tenant_a",
            user_id="user_a",
            session_id="session_a",
            trigger="fact",
        )
    )

    invalidated = runtime.invalidate(
        tenant_id="tenant_a",
        user_id="user_a",
        session_id="session_a",
        memory_ids=[result.records[0].memory_id],
    )
    read_result = runtime.read(
        MemoryReadQuery(
            tenant_id="tenant_a",
            user_id="user_a",
            session_id="session_a",
            scope="long_term",
            top_k=5,
        )
    )

    assert invalidated >= 1
    assert read_result.records == []


def test_memory_should_return_empty_result_when_extractor_returns_nothing() -> None:
    runtime, _ = _build_runtime({"items": []})

    result = runtime.write(
        MemoryWriteRequest(
            tenant_id="tenant_a",
            user_id="user_a",
            session_id="session_a",
            trigger="finish",
        )
    )

    assert result.records == []
    assert result.structured_written_count == 0


def test_memory_should_reject_missing_session_id_for_session_write() -> None:
    runtime, _ = _build_runtime({"items": []})

    with pytest.raises(ValueError):
        runtime.write(
            MemoryWriteRequest(
                tenant_id="tenant_a",
                user_id="user_a",
                session_id=None,
                trigger="finish",
            )
        )


def test_memory_store_get_by_ids_should_not_be_affected_by_top_k_ordering() -> None:
    store = InMemoryLongTermMemoryStore()
    records = [
        _build_runtime(
            {
                "items": [
                    {
                        "scope": "long_term",
                        "category": "fact",
                        "record_key": f"fact_{index}",
                        "content": f"事实 {index}",
                        "summary": f"摘要 {index}",
                        "source_excerpt": f"来源 {index}",
                    }
                ]
            }
        )[0].write(
            MemoryWriteRequest(
                tenant_id="tenant_a",
                user_id="user_a",
                session_id="session_a",
                trigger="fact",
            )
        ).records[0]
        for index in range(3)
    ]
    for record in records:
        store.upsert([record])

    result = store.get_by_ids(
        tenant_id="tenant_a",
        user_id="user_a",
        session_id=None,
        memory_ids=[records[0].memory_id],
    )

    assert len(result) == 1
    assert result[0].memory_id == records[0].memory_id


def test_memory_should_read_current_session_and_long_term_when_scope_is_unspecified_with_session_id() -> None:
    runtime, _ = _build_runtime({"items": []})
    session_result = runtime.write(
        MemoryWriteRequest(
            tenant_id="tenant_a",
            user_id="user_a",
            session_id="session_a",
            trigger="finish",
            extracted_items=[
                {
                    "scope": "session",
                    "category": "summary",
                    "record_key": "session_summary",
                    "content": "å½åä¼è¯æ­£å¨åå¤è£äºä¼ä¼è®®çºªè¦ã",
                    "summary": "åå¤è£äºä¼çºªè¦",
                    "source_excerpt": "è£äºä¼ä¼è®®çºªè¦",
                }
            ],
        )
    )
    long_term_result = runtime.write(
        MemoryWriteRequest(
            tenant_id="tenant_a",
            user_id="user_a",
            session_id="session_a",
            trigger="fact",
            extracted_items=[
                {
                    "scope": "long_term",
                    "category": "fact",
                    "record_key": "company_stage",
                    "content": "ç¨æ·å¬å¸å·²ç»å¬å¼æé²å¹´åº¦æ¥åã",
                    "summary": "å¬å¼æé²å¹´åº¦æ¥å",
                    "source_excerpt": "å¹´åº¦æ¥åæé²",
                }
            ],
        )
    )
    runtime._vector_store = _FakeVectorStore(  # type: ignore[attr-defined]
        hits_by_scope={
            "session": [MemoryVectorHit(memory_id=session_result.records[0].memory_id, score=0.95, metadata={"scope": "session", "session_id": "session_a"})],
            "long_term": [MemoryVectorHit(memory_id=long_term_result.records[0].memory_id, score=0.90, metadata={"scope": "long_term"})],
        }
    )

    result = runtime.read(
        MemoryReadQuery(
            tenant_id="tenant_a",
            user_id="user_a",
            session_id="session_a",
            scope=None,
            top_k=5,
            query_text="è£äºä¼çºªè¦åå¹´åº¦æ¥å",
        )
    )

    assert len(result.records) == 2
    assert {item.scope for item in result.records} == {"session", "long_term"}


def test_memory_should_treat_scope_none_without_session_id_as_long_term_only_for_vector_reads() -> None:
    runtime, _ = _build_runtime({"items": []})
    runtime._vector_store = _FakeVectorStore(  # type: ignore[attr-defined]
        hits_by_scope={
            "long_term": [MemoryVectorHit(memory_id="mem_long", score=0.88, metadata={"scope": "long_term"})],
        }
    )

    runtime.read(
        MemoryReadQuery(
            tenant_id="tenant_a",
            user_id="user_a",
            session_id=None,
            scope=None,
            top_k=5,
            query_text="é¿æåå¥½",
        )
    )

    assert len(runtime._vector_store.queries) == 1  # type: ignore[attr-defined]
    assert runtime._vector_store.queries[0].scope == "long_term"  # type: ignore[attr-defined]
    assert runtime._vector_store.queries[0].session_id is None  # type: ignore[attr-defined]


def test_memory_should_keep_explicit_source_type_from_extracted_item() -> None:
    runtime, _ = _build_runtime(
        {
            "items": [
                {
                    "scope": "long_term",
                    "category": "fact",
                    "record_key": "retrieval_fact",
                    "content": "ç¨æ·å¬å¸å·²ç»å¬å¼æé²å¹´åº¦æ¥åã",
                    "summary": "å¬å¼æé²å¹´åº¦æ¥å",
                    "source_type": "retrieval_citation",
                    "source_id": "cite_annual_report",
                    "source_excerpt": "å¹´åº¦æ¥åæé²",
                }
            ]
        }
    )

    result = runtime.write(
        MemoryWriteRequest(
            tenant_id="tenant_a",
            user_id="user_a",
            session_id="session_a",
            trigger="fact",
        )
    )

    assert len(result.records) == 1
    assert result.records[0].source.source_type == "retrieval_citation"
    assert result.records[0].source.source_id == "cite_annual_report"
