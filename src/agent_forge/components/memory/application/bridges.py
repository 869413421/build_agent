"""Memory 到上下文层的桥接函数。"""

from __future__ import annotations

from agent_forge.components.memory.domain import MemoryReadResult, MemoryRecord
from agent_forge.components.protocol import AgentMessage


def to_context_messages(result: MemoryReadResult, role: str = "developer") -> list[AgentMessage]:
    """把记忆读取结果桥接为上下文消息。

    Args:
        result: 读取结果。
        role: 注入到上下文中的消息角色。

    Returns:
        list[AgentMessage]: 可被上下文编排层继续消费的消息列表。
    """

    messages: list[AgentMessage] = []
    for record in result.records:
        messages.append(
            AgentMessage(
                role=role,  # type: ignore[arg-type]
                content=_format_memory_record(record),
                metadata={
                    "memory_id": record.memory_id,
                    "memory_scope": record.scope,
                    "memory_category": record.category,
                },
            )
        )
    return messages


def _format_memory_record(record: MemoryRecord) -> str:
    """格式化单条记忆为上下文文本。

    Args:
        record: 记忆记录。

    Returns:
        str: 结构化文本片段。
    """

    summary = record.summary or record.content
    return (
        f"[记忆][{record.scope}/{record.category}] {summary}\n"
        f"- key: {record.record_key}\n"
        f"- source: {record.source.source_type}\n"
        f"- updated_at: {record.updated_at}"
    )
