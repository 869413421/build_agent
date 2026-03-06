"""Engine(loop) 组件测试（asyncio 生产导向）。"""

from __future__ import annotations

import asyncio
import time

from agent_forge.components.engine import EngineLimits, EngineLoop, PlanStep, ReflectDecision, RunContext, StepOutcome
from agent_forge.components.protocol import AgentState, ErrorInfo, ExecutionEvent, build_initial_state


def test_engine_run_success_flow() -> None:
    """正常流程应输出 success 并产出 finish 事件。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=5, time_budget_ms=5000))
    state = build_initial_state("session_engine_success")

    def plan_fn(_: AgentState) -> list[str]:
        return ["step-a", "step-b"]

    async def act_fn(_: AgentState, step: PlanStep, idx: int) -> StepOutcome:
        return StepOutcome(status="ok", output={"step": step.name, "index": idx})

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))
    assert updated.final_answer is not None
    assert updated.final_answer.status == "success"
    assert updated.final_answer.output["success_steps"] == 2
    assert updated.final_answer.output["attempt_count"] == 2
    assert updated.events[-1].event_type == "finish"


def test_engine_reflect_retry_once_then_success() -> None:
    """可重试错误应触发 reflect 重试并最终成功。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=4, time_budget_ms=5000, max_retry_per_step=1))
    state = build_initial_state("session_engine_retry")
    call_count = {"count": 0}

    def plan_fn(_: AgentState) -> list[dict]:
        return [{"id": "s-a", "name": "step-a"}]

    async def act_fn(_: AgentState, __: PlanStep, ___: int) -> StepOutcome:
        call_count["count"] += 1
        if call_count["count"] == 1:
            return StepOutcome(
                status="error",
                output={},
                error=ErrorInfo(error_code="TEMP_FAIL", error_message="temp", retryable=True),
            )
        return StepOutcome(status="ok", output={"done": True})

    async def reflect_fn(_: AgentState, __: PlanStep, ___: int, outcome: StepOutcome) -> ReflectDecision:
        if outcome.status == "error" and outcome.error and outcome.error.retryable:
            return ReflectDecision(action="retry", reason="临时错误重试")
        return ReflectDecision(action="continue", reason="成功推进")

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn, reflect_fn=reflect_fn))
    assert updated.final_answer is not None
    assert updated.final_answer.status == "success"
    assert updated.final_answer.output["reflected_retry_count"] == 1
    assert updated.final_answer.output["attempt_count"] == 2


def test_engine_resume_uses_stable_step_key_not_idx() -> None:
    """plan 重排后仍应根据 stable step key 跳过已完成步骤。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=10, time_budget_ms=5000))
    state = build_initial_state("session_engine_resume")
    state.events.append(
        ExecutionEvent(
            trace_id=state.trace_id,
            run_id=state.run_id,
            step_id="step_old",
            event_type="state_update",
            payload={"phase": "update", "step_key": "s-b", "step_name": "step-b", "output": {"ok": True}},
        )
    )
    called_steps: list[str] = []

    def plan_fn(_: AgentState) -> list[dict]:
        return [
            {"id": "s-x", "name": "step-x"},
            {"id": "s-b", "name": "step-b"},
            {"id": "s-a", "name": "step-a"},
        ]

    async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
        called_steps.append(step.name)
        return StepOutcome(status="ok", output={"step": step.name})

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))
    assert "step-b" not in called_steps
    assert "step-x" in called_steps
    assert "step-a" in called_steps
    assert updated.final_answer is not None
    assert updated.final_answer.output["skipped_steps"] == 1


def test_engine_max_steps_counts_executed_not_skipped() -> None:
    """max_steps 只统计实际执行步骤，不统计 resume_skip。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=1, time_budget_ms=5000))
    state = build_initial_state("session_engine_max_steps")
    state.events.append(
        ExecutionEvent(
            trace_id=state.trace_id,
            run_id=state.run_id,
            step_id="step_old",
            event_type="state_update",
            payload={"phase": "update", "step_key": "s-a", "step_name": "step-a", "output": {"ok": True}},
        )
    )

    def plan_fn(_: AgentState) -> list[dict]:
        return [{"id": "s-a", "name": "step-a"}, {"id": "s-b", "name": "step-b"}]

    async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
        return StepOutcome(status="ok", output={"step": step.name})

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))
    assert updated.final_answer is not None
    assert updated.final_answer.status == "success"
    assert updated.final_answer.output["executed_steps"] == 1
    assert updated.final_answer.output["skipped_steps"] == 1


def test_engine_step_timeout_via_executor() -> None:
    """单步超时应转换为 STEP_TIMEOUT 错误。"""

    engine = EngineLoop(
        limits=EngineLimits(max_steps=2, time_budget_ms=5000, step_timeout_ms=10, max_retry_per_step=0)
    )
    state = build_initial_state("session_engine_timeout")

    def plan_fn(_: AgentState) -> list[dict]:
        return [{"id": "s-a", "name": "slow-step"}]

    async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
        await asyncio.sleep(0.05)
        return StepOutcome(status="ok", output={"late": True})

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))
    assert updated.final_answer is not None
    assert updated.final_answer.status == "failed"
    assert any(e.error and e.error.error_code == "STEP_TIMEOUT" for e in updated.events if e.event_type == "error")


def test_engine_context_fields_recorded_in_events() -> None:
    """隔离上下文与版本信息应写入 plan/finish 事件。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=2, time_budget_ms=5000))
    state = build_initial_state("session_engine_ctx")

    def plan_fn(_: AgentState) -> list[dict]:
        return [{"id": "s-a", "name": "step-a"}]

    async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
        return StepOutcome(status="ok", output={"step": step.name})

    ctx = RunContext(
        tenant_id="tenant-001",
        user_id="user-001",
        config_version="cfg-20260301",
        model_version="model-v1",
        tool_version="tool-v1",
        policy_version="policy-v1",
    )
    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn, context=ctx))
    assert any(
        e.event_type == "plan" and e.payload.get("context", {}).get("tenant_id") == "tenant-001" for e in updated.events
    )
    assert any(
        e.event_type == "finish" and e.payload.get("context", {}).get("policy_version") == "policy-v1"
        for e in updated.events
    )


def test_engine_backpressure_error_when_inflight_exceeded() -> None:
    """并发门达到上限时应返回 ACT_BACKPRESSURE。"""

    engine = EngineLoop(
        limits=EngineLimits(max_steps=1, time_budget_ms=5000, step_timeout_ms=10, max_retry_per_step=0, max_inflight_acts=1)
    )
    state = build_initial_state("session_engine_backpressure")

    async def scenario() -> AgentState:
        await engine._inflight_guard.acquire()
        try:
            def plan_fn(_: AgentState) -> list[dict]:
                return [{"id": "s-a", "name": "step-a"}]

            async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
                return StepOutcome(status="ok", output={"step": step.name})

            return await engine.arun(state, plan_fn=plan_fn, act_fn=act_fn)
        finally:
            engine._inflight_guard.release()

    updated = asyncio.run(scenario())
    assert updated.final_answer is not None
    assert updated.final_answer.status == "failed"
    assert any(e.error and e.error.error_code == "ACT_BACKPRESSURE" for e in updated.events if e.event_type == "error")


def test_engine_should_not_fail_when_event_listener_raises() -> None:
    """监听器异常不应影响主流程完成。"""

    def listener(_: ExecutionEvent) -> None:
        raise RuntimeError("listener boom")

    engine = EngineLoop(
        limits=EngineLimits(max_steps=1, time_budget_ms=5000),
        event_listener=listener,
    )
    state = build_initial_state("session_engine_listener")

    def plan_fn(_: AgentState) -> list[dict]:
        return [{"id": "s-a", "name": "step-a"}]

    async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
        return StepOutcome(status="ok", output={"step": step.name, "idx": step_idx})

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))
    assert updated.final_answer is not None
    assert updated.final_answer.status == "success"


