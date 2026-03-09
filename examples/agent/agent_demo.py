"""最小 `Agent()` 示例。"""

from __future__ import annotations

import asyncio

from agent_forge import Agent


async def run_demo() -> dict[str, object]:
    """运行最小 `Agent()` 示例。"""

    agent = Agent()
    result = await agent.arun("帮我总结一下这次任务材料还缺什么？")
    return {
        "status": result.status,
        "summary": result.summary,
        "output": result.output,
        "trace_id": result.trace_id,
        "session_id": result.session_id,
    }


if __name__ == "__main__":
    print(asyncio.run(run_demo()))
