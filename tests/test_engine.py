"""Engine(loop) 组件测试。"""

from __future__ import annotations

from labor_agent.core.engine import EngineLimits, EngineLoop, StepOutcome
from labor_agent.core.protocol import AgentState, ErrorInfo, build_initial_state


def test_engine_run_success_flow() -> None:
    """正常流程应输出 success 并产出 finish 事件。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=5, time_budget_ms=5000))
    state = build_initial_state("session_engine_success")

    def plan_fn(_: AgentState) -> list[str]:
        return ["step-a", "step-b"]

    def act_fn(_: AgentState, step: str, idx: int) -> StepOutcome:
        return StepOutcome(status="ok", output={"step": step, "index": idx})

    updated = engine.run(state, plan_fn=plan_fn, act_fn=act_fn)
    assert updated.final_answer is not None
    assert updated.final_answer.status == "success"
    assert updated.final_answer.output["success_steps"] == 2
    assert updated.events[-1].event_type == "finish"


def test_engine_stops_when_max_steps_reached() -> None:
    """超步数应停止并返回 partial。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=1, time_budget_ms=5000))
    state = build_initial_state("session_engine_steps")

    def plan_fn(_: AgentState) -> list[str]:
        return ["step-a", "step-b", "step-c"]

    def act_fn(_: AgentState, step: str, idx: int) -> StepOutcome:
        return StepOutcome(status="ok", output={"step": step, "index": idx})

    updated = engine.run(state, plan_fn=plan_fn, act_fn=act_fn)
    assert updated.final_answer is not None
    assert updated.final_answer.status == "partial"
    assert updated.final_answer.output["stop_reason"] == "max_steps_reached"
    assert any(e.event_type == "error" for e in updated.events)


def test_engine_stops_when_step_failed() -> None:
    """步骤失败应停止并返回 failed。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=5, time_budget_ms=5000))
    state = build_initial_state("session_engine_failed")

    def plan_fn(_: AgentState) -> list[str]:
        return ["step-a", "step-b"]

    def act_fn(_: AgentState, step: str, idx: int) -> StepOutcome:
        if idx == 2:
            return StepOutcome(
                status="error",
                output={"step": step},
                error=ErrorInfo(
                    error_code="MOCK_STEP_FAIL",
                    error_message="mock fail",
                    retryable=False,
                ),
            )
        return StepOutcome(status="ok", output={"step": step})

    updated = engine.run(state, plan_fn=plan_fn, act_fn=act_fn)
    assert updated.final_answer is not None
    assert updated.final_answer.status == "failed"
    assert updated.final_answer.output["failed_steps"] == 1

