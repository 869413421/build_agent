"""Safety ToolRuntime hook 测试。"""

from __future__ import annotations

from agent_forge.components.observability import ObservabilityRuntime
from agent_forge.components.protocol import ToolCall
from agent_forge.components.safety import SafetyRuntime, SafetyToolRuntimeHook
from agent_forge.components.tool_runtime import ToolRuntime, ToolSpec


def test_safety_tool_hook_should_block_handler_for_high_risk_tool() -> None:
    runtime = ToolRuntime()
    executed = {"count": 0}

    def _handler(_: dict) -> dict:
        executed["count"] += 1
        return {"ok": True}

    runtime.register_tool(ToolSpec(name="dangerous_write", side_effect_level="high"), _handler)
    runtime.register_hook(
        SafetyToolRuntimeHook(
            SafetyRuntime(),
            spec_resolver=runtime.get_tool_spec,
            capability_resolver=lambda principal: {"read"} if principal == "intern" else {"safety:tool:high_risk"},
        )
    )

    result = runtime.execute(
        ToolCall(tool_call_id="tc_hook_deny", tool_name="dangerous_write", args={"target": "prod"}, principal="intern")
    )

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "TOOL_SAFETY_DENIED"
    assert executed["count"] == 0


def test_safety_tool_hook_should_allow_approved_high_risk_tool() -> None:
    runtime = ToolRuntime()
    runtime.register_tool(ToolSpec(name="dangerous_write", side_effect_level="high"), lambda args: {"target": args["target"]})
    runtime.register_hook(
        SafetyToolRuntimeHook(
            SafetyRuntime(),
            spec_resolver=runtime.get_tool_spec,
            capability_resolver=lambda _principal: {"safety:tool:high_risk"},
        )
    )

    result = runtime.execute(
        ToolCall(tool_call_id="tc_hook_allow", tool_name="dangerous_write", args={"target": "staging"}, principal="lead")
    )

    assert result.status == "ok"
    assert result.output["target"] == "staging"


def test_safety_tool_hook_should_use_runtime_capabilities_when_execute_supplies_them() -> None:
    runtime = ToolRuntime()
    runtime.register_tool(ToolSpec(name="dangerous_write", side_effect_level="high"), lambda args: {"target": args["target"]})
    runtime.register_hook(
        SafetyToolRuntimeHook(
            SafetyRuntime(),
            spec_resolver=runtime.get_tool_spec,
            capability_resolver=lambda _principal: set(),
        )
    )

    result = runtime.execute(
        ToolCall(tool_call_id="tc_hook_runtime_caps", tool_name="dangerous_write", args={"target": "prod"}, principal="lead"),
        capabilities={"safety:tool:high_risk"},
    )

    assert result.status == "ok"
    assert result.output["target"] == "prod"


def test_safety_tool_hook_should_flow_into_observability_error_trace() -> None:
    observability = ObservabilityRuntime()
    runtime = ToolRuntime(hooks=[observability.build_tool_hook()])
    runtime.register_tool(ToolSpec(name="dangerous_write", side_effect_level="high"), lambda _: {"ok": True})
    runtime.register_hook(
        SafetyToolRuntimeHook(
            SafetyRuntime(),
            spec_resolver=runtime.get_tool_spec,
            capability_resolver=lambda _principal: set(),
        )
    )

    observability.set_default_context("trace_safety_hook", "run_safety_hook")
    runtime.execute(
        ToolCall(tool_call_id="tc_obs_deny", tool_name="dangerous_write", args={"password": "secret"}, principal="intern")
    )

    traces = observability.trace_sink.query_traces(trace_id="trace_safety_hook", run_id="run_safety_hook")
    assert any(item.error_code == "TOOL_SAFETY_DENIED" for item in traces)
