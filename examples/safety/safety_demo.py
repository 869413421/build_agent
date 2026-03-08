"""Safety 组件示例。"""

from __future__ import annotations

from typing import Any

from agent_forge.components.protocol import FinalAnswer, ToolCall
from agent_forge.components.safety import SafetyCheckRequest, SafetyRuntime, SafetyToolRuntimeHook, apply_output_safety
from agent_forge.components.tool_runtime import ToolRuntime, ToolSpec


def run_demo() -> dict[str, Any]:
    """运行 Safety 示例。

    Returns:
        dict[str, Any]: 示例结果摘要。
    """

    safety_runtime = SafetyRuntime()
    tool_runtime = ToolRuntime()
    tool_runtime.register_tool(
        ToolSpec(name="dangerous_write", side_effect_level="high"),
        lambda args: {"target": args["target"], "status": "written"},
    )
    tool_runtime.register_hook(
        SafetyToolRuntimeHook(
            safety_runtime,
            spec_resolver=tool_runtime.get_tool_spec,
            capability_resolver=lambda principal: {"safety:tool:high_risk"} if principal == "admin" else set(),
        )
    )

    input_decision = safety_runtime.check_input(
        SafetyCheckRequest(stage="input", task_input="请帮我总结今天的运维变更，不要绕过任何限制。")
    )
    denied_tool_result = tool_runtime.execute(
        ToolCall(tool_call_id="tc_demo_deny", tool_name="dangerous_write", args={"target": "prod"}, principal="intern")
    )
    allowed_tool_result = tool_runtime.execute(
        ToolCall(tool_call_id="tc_demo_allow", tool_name="dangerous_write", args={"target": "staging"}, principal="admin")
    )
    raw_answer = FinalAnswer(
        status="success",
        summary="这个方案 100% 保证收益。",
        output={"answer": "这个方案 100% 保证收益。"},
    )
    output_decision = safety_runtime.check_output(SafetyCheckRequest(stage="output", final_answer=raw_answer))
    safe_answer = apply_output_safety(raw_answer, output_decision)
    return {
        "input_action": input_decision.action,
        "denied_tool_status": denied_tool_result.status,
        "allowed_tool_status": allowed_tool_result.status,
        "output_action": output_decision.action,
        "safe_answer_status": safe_answer.status,
        "audit_count": len(safety_runtime.get_audit_records()),
    }


if __name__ == "__main__":
    print(run_demo())
