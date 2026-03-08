"""Memory 到上下文桥接测试。"""

from __future__ import annotations

from agent_forge.components.memory import MemoryReadResult, MemoryRecord, MemorySource, to_context_messages


def test_memory_bridge_should_convert_records_into_context_messages() -> None:
    result = MemoryReadResult(
        records=[
            MemoryRecord(
                record_key="pref_language",
                scope="long_term",
                tenant_id="tenant_a",
                user_id="user_a",
                session_id=None,
                category="preference",
                content="用户偏好中文输出。",
                summary="偏好中文输出",
                source=MemorySource(source_type="agent_message", source_excerpt="请用中文"),
            )
        ],
        total_matched=1,
        scope="long_term",
    )

    messages = to_context_messages(result)

    assert len(messages) == 1
    assert messages[0].role == "developer"
    assert "偏好中文输出" in messages[0].content


def test_memory_bridge_should_keep_scope_and_category_labels() -> None:
    result = MemoryReadResult(
        records=[
            MemoryRecord(
                record_key="session_summary",
                scope="session",
                tenant_id="tenant_a",
                user_id="user_a",
                session_id="session_a",
                category="summary",
                content="会话摘要",
                summary="会话摘要",
                source=MemorySource(source_type="final_answer", source_excerpt="会话摘要"),
            ),
            MemoryRecord(
                record_key="customer_stage",
                scope="long_term",
                tenant_id="tenant_a",
                user_id="user_a",
                session_id=None,
                category="fact",
                content="客户正在准备 A 轮融资。",
                summary="客户准备 A 轮融资",
                source=MemorySource(source_type="tool_result", source_excerpt="A 轮融资"),
            ),
        ],
        total_matched=2,
    )

    messages = to_context_messages(result)

    assert "[记忆][session/summary]" in messages[0].content
    assert "[记忆][long_term/fact]" in messages[1].content
