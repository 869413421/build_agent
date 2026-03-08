"""Memory 桥接到 Context Engineering 的演示脚本。"""

from __future__ import annotations

from typing import Any

from agent_forge.components.memory import MemoryReadQuery, MemoryRuntime, to_context_messages

from examples.memory.memory_demo import DemoModelRuntime
from agent_forge.components.memory import (
    MemoryExtractor,
    MemoryWriteRequest,
    InMemoryLongTermMemoryStore,
    InMemorySessionMemoryStore,
)


def run_bridge_demo() -> dict[str, Any]:
    """演示记忆写入后如何桥接成上下文消息。

    Returns:
        dict[str, Any]: 桥接结果摘要。
    """

    runtime = MemoryRuntime(
        extractor=MemoryExtractor(model_runtime=DemoModelRuntime()),
        session_store=InMemorySessionMemoryStore(),
        long_term_store=InMemoryLongTermMemoryStore(),
    )
    runtime.write(
        MemoryWriteRequest(
            tenant_id="tenant_demo",
            user_id="user_demo",
            session_id="session_demo",
            trigger="finish",
        )
    )
    read_result = runtime.read(
        MemoryReadQuery(
            tenant_id="tenant_demo",
            user_id="user_demo",
            session_id="session_demo",
            scope=None,
            top_k=5,
        )
    )
    messages = to_context_messages(read_result)
    return {
        "record_count": len(read_result.records),
        "message_count": len(messages),
        "message_roles": [item.role for item in messages],
        "first_message": messages[0].content if messages else "",
    }


if __name__ == "__main__":
    print(run_bridge_demo())
