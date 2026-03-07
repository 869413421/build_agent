"""第七章：Context Engineering 端到端可运行示例。"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from agent_forge.components.context_engineering import (
    CitationItem,
    ContextBudget,
    ContextEngineeringHook,
    ContextEngineeringRuntime,
)
from agent_forge.components.model_runtime import (
    ModelRequest,
    ModelResponse,
    ModelRuntime,
    ModelStats,
    ProviderAdapter,
)
from agent_forge.components.model_runtime.domain import ModelStreamEvent
from agent_forge.components.protocol import AgentMessage


class DemoCaptureAdapter(ProviderAdapter):
    """用于演示 Hook 改写结果的捕获适配器。"""

    def __init__(self) -> None:
        self.captured_request: ModelRequest | None = None

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        """捕获最终请求并返回固定响应。"""

        self.captured_request = request
        return ModelResponse(
            content='{"status":"ok","message":"context engineered"}',
            stats=ModelStats(total_tokens=32, prompt_tokens=24, completion_tokens=8, latency_ms=10),
        )

    def generate_stream(self, request: ModelRequest, **kwargs: Any) -> Iterator[ModelStreamEvent]:
        """返回最小流式事件，满足抽象接口要求。"""

        yield ModelStreamEvent(
            event_type="start",
            request_id=request.request_id or "ctx_demo",
            sequence=0,
            timestamp_ms=0,
        )
        yield ModelStreamEvent(
            event_type="end",
            request_id=request.request_id or "ctx_demo",
            sequence=1,
            content='{"status":"ok"}',
            timestamp_ms=0,
        )


def build_demo_runtime() -> tuple[ModelRuntime, DemoCaptureAdapter]:
    """构造演示用的 ModelRuntime 与捕获适配器。"""

    adapter = DemoCaptureAdapter()
    return ModelRuntime(adapter=adapter), adapter


def build_demo_hook() -> ContextEngineeringHook:
    """构造演示用的 ContextEngineeringHook。"""

    runtime = ContextEngineeringRuntime()
    return ContextEngineeringHook(
        runtime,
        budget=ContextBudget(max_input_tokens=220, reserved_output_tokens=40, min_latest_user_tokens=8),
        developer_prompt="必须输出 JSON，并优先使用保留下来的引用。",
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "search_policy",
                    "description": "查询制度材料",
                },
            }
        ],
    )


def build_demo_request() -> ModelRequest:
    """构造一个会触发裁剪的长上下文请求。"""

    return ModelRequest(
        system_prompt="你是一名严谨的政策分析助手。",
        messages=[
            AgentMessage(role="assistant", content="old-summary-" + ("A" * 180)),
            AgentMessage(role="user", content="old-question-" + ("B" * 320)),
            AgentMessage(role="assistant", content="middle-summary-" + ("C" * 220)),
            AgentMessage(
                role="user",
                content="latest-user-请结合制度材料说明试用期工资和转正工资的关系。" + ("D" * 96),
            ),
        ],
        citations=[
            CitationItem(
                source_id="policy-001",
                title="劳动合同管理办法",
                url="https://example.com/policy-001",
                snippet="试用期工资不得低于转正工资的一定比例。",
            ).model_dump(),
            CitationItem(
                source_id="policy-002",
                title="工资支付实施细则",
                url="https://example.com/policy-002",
                snippet="工资支付规则应与劳动合同和制度文件一致。",
            ).model_dump(),
        ],
        request_id="ctx_demo_request",
    )


def run_demo() -> dict[str, Any]:
    """运行演示并返回可断言的结果结构。"""

    # 1. 构造运行时与 Hook，形成“请求进入模型前”的治理链路。
    runtime, adapter = build_demo_runtime()
    hook = build_demo_hook()

    # 2. 构造长上下文请求，让裁剪策略有机会真正生效。
    request = build_demo_request()

    # 3. 通过 ModelRuntime 触发 Hook，拿到被改写后的最终请求。
    response = runtime.generate(request, hooks=hook)
    captured = adapter.captured_request
    if captured is None:
        raise RuntimeError("演示失败：未捕获到最终请求。")

    # 4. 提取对教程最有解释价值的输出：消息、工具和预算报告。
    budget_report = captured.extra_kwargs().get("context_budget_report", {})
    return {
        "response_content": response.content,
        "final_system_prompt": captured.system_prompt,
        "final_messages": [
            {"role": item.role, "content": item.content}
            for item in captured.messages
        ],
        "final_tools": captured.tools or [],
        "budget_report": budget_report,
    }


def print_demo_result(result: dict[str, Any]) -> None:
    """以适合教程展示的方式打印演示结果。"""

    print("=== response ===")
    print(result["response_content"])
    print()

    print("=== final messages ===")
    for index, message in enumerate(result["final_messages"], start=1):
        content = message["content"]
        preview = content if len(content) <= 120 else content[:120] + "..."
        print(f"[{index}] role={message['role']} content={preview}")
    print()

    print("=== final tools ===")
    print(json.dumps(result["final_tools"], ensure_ascii=False, indent=2))
    print()

    print("=== budget report ===")
    print(json.dumps(result["budget_report"], ensure_ascii=False, indent=2))


def main() -> None:
    """运行第七章示例。"""

    # 1. 执行完整示例，得到最终请求与预算报告。
    result = run_demo()

    # 2. 打印关键输出，帮助读者观察裁剪后的真实上下文。
    print_demo_result(result)


if __name__ == "__main__":
    main()
