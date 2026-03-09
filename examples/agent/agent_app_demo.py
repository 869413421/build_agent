"""最小 `AgentApp()` 示例。"""

from __future__ import annotations

import asyncio

from agent_forge import AgentApp


async def run_demo() -> dict[str, object]:
    """运行最小 `AgentApp()` 示例。"""

    # 1. 先初始化应用级装配入口；`default` 模型已内置注册。
    app = AgentApp()
    # 2. 再按名字装配出一个具体 agent。
    agent = app.create_agent(
        name="researcher",
        model="default",
    )
    # 3. 最后通过 agent 执行任务，证明主入口已经收口为 `AgentApp -> Agent`。
    result = await agent.arun("帮我总结一下这个主题。")
    return {
        "agent_name": agent.name,
        "status": result.status,
        "summary": result.summary,
        "output": result.output,
        "trace_id": result.trace_id,
        "session_id": result.session_id,
    }


if __name__ == "__main__":
    print(asyncio.run(run_demo()))
