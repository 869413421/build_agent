"""Tool Runtime 与 Engine 的零侵入集成测试。"""

from __future__ import annotations

import asyncio

from agent_forge.components.engine import EngineLimits, EngineLoop, PlanStep, StepOutcome
from agent_forge.components.protocol import AgentState, ToolCall, build_initial_state
from agent_forge.components.tool_runtime import ToolRuntime, ToolSpec


def test_engine_should_execute_tool_runtime_via_act_fn() -> None:
    engine = EngineLoop(limits=EngineLimits(max_steps=3, time_budget_ms=5000))
    runtime = ToolRuntime()
    runtime.register_tool(ToolSpec(name="echo"), lambda args: {"echo": args["text"]})
    state = build_initial_state("session_engine_tool_runtime_success")

    def plan_fn(_: AgentState) -> list[dict]:
        return [{"id": "s1", "name": "tool-echo", "payload": {"tool_call_id": "tc_100", "tool_name": "echo", "args": {"text": "hi"}}}]

    async def act_fn(current_state: AgentState, step: PlanStep, _: int) -> StepOutcome:
        call = _build_tool_call(step.payload)
        current_state.tool_calls.append(call)
        result = runtime.execute(call)
        current_state.tool_results.append(result)
        if result.status == "ok":
            return StepOutcome(status="ok", output=result.output)
        return StepOutcome(status="error", output=result.output, error=result.error)

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))
    assert updated.final_answer is not None
    assert updated.final_answer.status == "success"
    assert updated.tool_results[0].status == "ok"
    assert updated.tool_results[0].output["echo"] == "hi"


def test_engine_tool_runtime_should_not_repeat_side_effects_with_same_call_id() -> None:
    engine = EngineLoop(limits=EngineLimits(max_steps=4, time_budget_ms=5000))
    runtime = ToolRuntime()
    counter = {"value": 0}

    def _counter_handler(_: dict) -> dict:
        counter["value"] += 1
        return {"counter": counter["value"]}

    runtime.register_tool(ToolSpec(name="counter"), _counter_handler)
    state = build_initial_state("session_engine_tool_runtime_idempotent")

    def plan_fn(_: AgentState) -> list[dict]:
        return [
            {"id": "s1", "name": "count-1", "payload": {"tool_call_id": "tc_same", "tool_name": "counter", "args": {}}},
            {"id": "s2", "name": "count-2", "payload": {"tool_call_id": "tc_same", "tool_name": "counter", "args": {}}},
        ]

    async def act_fn(current_state: AgentState, step: PlanStep, _: int) -> StepOutcome:
        call = _build_tool_call(step.payload)
        current_state.tool_calls.append(call)
        result = runtime.execute(call)
        current_state.tool_results.append(result)
        if result.status == "ok":
            return StepOutcome(status="ok", output=result.output)
        return StepOutcome(status="error", output=result.output, error=result.error)

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))
    assert updated.final_answer is not None
    assert updated.final_answer.status == "success"
    assert counter["value"] == 1
    assert len(updated.tool_results) == 2
    assert updated.tool_results[0].output["counter"] == 1
    assert updated.tool_results[1].output["counter"] == 1


def test_engine_should_fail_when_tool_runtime_returns_error() -> None:
    engine = EngineLoop(limits=EngineLimits(max_steps=2, time_budget_ms=5000, max_retry_per_step=0))
    runtime = ToolRuntime()
    state = build_initial_state("session_engine_tool_runtime_fail")

    def plan_fn(_: AgentState) -> list[dict]:
        return [{"id": "s1", "name": "missing-tool", "payload": {"tool_call_id": "tc_404", "tool_name": "missing", "args": {}}}]

    async def act_fn(current_state: AgentState, step: PlanStep, _: int) -> StepOutcome:
        call = _build_tool_call(step.payload)
        current_state.tool_calls.append(call)
        result = runtime.execute(call)
        current_state.tool_results.append(result)
        if result.status == "ok":
            return StepOutcome(status="ok", output=result.output)
        return StepOutcome(status="error", output=result.output, error=result.error)

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))
    assert updated.final_answer is not None
    assert updated.final_answer.status == "failed"
    assert any(e.event_type == "error" for e in updated.events)
    assert updated.tool_results[0].error is not None
    assert updated.tool_results[0].error.error_code == "TOOL_NOT_FOUND"


def _build_tool_call(payload: dict) -> ToolCall:
    return ToolCall(
        tool_call_id=str(payload.get("tool_call_id", "")),
        tool_name=str(payload.get("tool_name", "")),
        args=payload.get("args", {}),
        principal="engine",
    )

