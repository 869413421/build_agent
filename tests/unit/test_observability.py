"""Observability 组件测试。"""

from __future__ import annotations

import asyncio

from agent_forge.components.engine import EngineLimits, EngineLoop, PlanStep, StepOutcome
from agent_forge.components.observability import ObservabilityRuntime, RedactionPolicy, SamplingPolicy
from agent_forge.components.protocol import AgentState, ErrorInfo, ToolCall, ToolResult, build_initial_state
from agent_forge.components.tool_runtime import ToolRuntime, ToolSpec


def test_observability_should_capture_engine_events_and_aggregate_metrics() -> None:
    observability = ObservabilityRuntime(sampling_policy=SamplingPolicy(success_sample_rate=1.0))
    state = build_initial_state("session_obs_engine")
    observability.set_default_context(trace_id=state.trace_id, run_id=state.run_id)
    engine = EngineLoop(
        limits=EngineLimits(max_steps=2, time_budget_ms=5000),
        event_listener=observability.engine_event_listener,
    )

    def plan_fn(_: AgentState) -> list[dict]:
        return [{"id": "s1", "name": "simple-step", "payload": {}}]

    async def act_fn(_: AgentState, __: PlanStep, ___: int) -> StepOutcome:
        return StepOutcome(status="ok", output={"message": "done"})

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))
    assert updated.final_answer is not None
    exported = observability.export(trace_id=state.trace_id, run_id=state.run_id)
    assert len(exported.traces) >= 3
    metrics = observability.aggregate_metrics(trace_id=state.trace_id, run_id=state.run_id)
    assert metrics["success_rate"] > 0
    assert metrics["failure_rate"] == 0


def test_observability_should_redact_sensitive_fields() -> None:
    observability = ObservabilityRuntime(
        sampling_policy=SamplingPolicy(success_sample_rate=1.0),
        redaction_policy=RedactionPolicy(masked_keys={"token", "api_key"}),
    )
    state = build_initial_state("session_obs_redact")
    observability.set_default_context(trace_id=state.trace_id, run_id=state.run_id)

    call = ToolCall(
        tool_call_id="tc_redact",
        tool_name="echo",
        principal="tester",
        args={"token": "raw-secret", "query": "hello"},
    )
    result = ToolResult(tool_call_id="tc_redact", status="ok", output={"api_key": "raw-key", "value": "ok"})
    observability.capture_tool_result(tool_call=call, result=result)

    bundle = observability.replay_structure(trace_id=state.trace_id, run_id=state.run_id)
    assert len(bundle.tool_records) == 1
    assert bundle.tool_records[0]["args_masked"]["token"] == "***"
    assert bundle.tool_records[0]["output"]["api_key"] == "***"


def test_observability_should_capture_tool_runtime_hook_events() -> None:
    observability = ObservabilityRuntime(sampling_policy=SamplingPolicy(success_sample_rate=1.0))
    observability.set_default_context(trace_id="trace_tool", run_id="run_tool")
    runtime = ToolRuntime()
    runtime.register_hook(observability.build_tool_hook())
    runtime.register_tool(ToolSpec(name="echo"), lambda args: {"echo": args["text"]})

    result = runtime.execute(
        ToolCall(tool_call_id="tc_01", tool_name="echo", args={"text": "hello"}, principal="tester")
    )
    assert result.status == "ok"

    export = observability.export(trace_id="trace_tool", run_id="run_tool")
    assert any(item.source == "tool_runtime" for item in export.traces)
    replay = observability.replay_structure(trace_id="trace_tool", run_id="run_tool")
    assert len(replay.tool_records) == 1
    assert replay.tool_records[0]["tool_call_id"] == "tc_01"


def test_observability_should_keep_error_event_when_sampling_zero() -> None:
    observability = ObservabilityRuntime(
        sampling_policy=SamplingPolicy(success_sample_rate=0.0, keep_error_events=True),
    )
    state = build_initial_state("session_obs_error")
    observability.set_default_context(trace_id=state.trace_id, run_id=state.run_id)

    error_step = StepOutcome(
        status="error",
        output={},
        error=ErrorInfo(error_code="X_FAIL", error_message="boom", retryable=False),
    )

    def plan_fn(_: AgentState) -> list[dict]:
        return [{"id": "s1", "name": "fail-step", "payload": {}}]

    async def act_fn(_: AgentState, __: PlanStep, ___: int) -> StepOutcome:
        return error_step

    engine = EngineLoop(
        limits=EngineLimits(max_steps=2, time_budget_ms=5000, max_retry_per_step=0),
        event_listener=observability.engine_event_listener,
    )
    asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))

    export = observability.export(trace_id=state.trace_id, run_id=state.run_id)
    assert any(item.error_code == "X_FAIL" for item in export.traces)


def test_observability_should_record_failed_tool_result_in_replay() -> None:
    observability = ObservabilityRuntime(sampling_policy=SamplingPolicy(success_sample_rate=1.0))
    observability.set_default_context(trace_id="trace_fail_tool", run_id="run_fail_tool")
    runtime = ToolRuntime()
    runtime.register_hook(observability.build_tool_hook())

    result = runtime.execute(
        ToolCall(tool_call_id="tc_missing", tool_name="missing", args={}, principal="tester")
    )
    assert result.status == "error"
    replay = observability.replay_structure(trace_id="trace_fail_tool", run_id="run_fail_tool")
    assert len(replay.tool_records) == 1
    assert replay.tool_records[0]["status"] == "error"


def test_observability_should_not_mix_context_across_concurrent_tasks() -> None:
    observability = ObservabilityRuntime(sampling_policy=SamplingPolicy(success_sample_rate=1.0))
    runtime = ToolRuntime()
    runtime.register_hook(observability.build_tool_hook())
    runtime.register_tool(ToolSpec(name="echo"), lambda args: {"echo": args["text"]})

    async def _run_one(trace_id: str, run_id: str, call_id: str, text: str) -> None:
        observability.set_default_context(trace_id=trace_id, run_id=run_id)
        await runtime.execute_async(
            ToolCall(tool_call_id=call_id, tool_name="echo", args={"text": text}, principal="tester")
        )

    async def _run_both() -> None:
        await asyncio.gather(
            _run_one("trace_a", "run_a", "tc_a", "A"),
            _run_one("trace_b", "run_b", "tc_b", "B"),
        )

    asyncio.run(_run_both())

    replay_a = observability.replay_structure(trace_id="trace_a", run_id="run_a")
    replay_b = observability.replay_structure(trace_id="trace_b", run_id="run_b")
    assert len(replay_a.tool_records) == 1
    assert len(replay_b.tool_records) == 1
    assert replay_a.tool_records[0]["tool_call_id"] == "tc_a"
    assert replay_b.tool_records[0]["tool_call_id"] == "tc_b"
