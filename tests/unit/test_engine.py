"""Engine(loop) 组件测试（asyncio 生产导向）。"""

from __future__ import annotations

import asyncio

from agent_forge.components.engine import (
    EngineLimits,
    ExecutionPlan,
    EngineLoop,
    EnginePipelineContext,
    EngineStage,
    PlanAudit,
    PlanStep,
    ReflectDecision,
    RunContext,
    StepOutcome,
)
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


def test_engine_should_allow_pipeline_stage_to_expand_plan() -> None:
    """顶层 pipeline 应允许插入新阶段并修改计划步骤。"""

    def pipeline_customizer(stages: list[EngineStage]) -> list[EngineStage]:
        async def expand_plan(context: EnginePipelineContext) -> None:
            context.append_plan_steps([PlanStep(key="s-b", name="step-b", payload={})])
            assert context.current_plan is not None
            assert [step.name for step in context.current_plan.steps] == ["step-a", "step-b"]
            context.append_event(
                event_type="state_update",
                step_id="step_plan_extend",
                payload={"phase": "plan_expand", "added_step": "step-b"},
            )

        return [stages[0], EngineStage(name="expand_plan", handler=expand_plan), *stages[1:]]

    engine = EngineLoop(
        limits=EngineLimits(max_steps=4, time_budget_ms=5000),
        pipeline_customizer=pipeline_customizer,
    )
    state = build_initial_state("session_engine_pipeline_extension")
    called_steps: list[str] = []

    def plan_fn(_: AgentState) -> list[dict]:
        return [{"id": "s-a", "name": "step-a"}]

    async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
        called_steps.append(step.name)
        return StepOutcome(status="ok", output={"step": step.name, "idx": step_idx})

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))
    assert called_steps == ["step-a", "step-b"]
    assert updated.final_answer is not None
    assert updated.final_answer.output["success_steps"] == 2
    assert any(e.payload.get("phase") == "plan_expand" for e in updated.events if e.event_type == "state_update")


def test_engine_should_schedule_steps_by_dependencies_and_priority() -> None:
    """计划中的依赖和优先级应真正影响执行顺序。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=4, time_budget_ms=5000))
    state = build_initial_state("session_engine_schedule")
    called_steps: list[str] = []

    def plan_fn(_: AgentState) -> ExecutionPlan:
        return ExecutionPlan(
            global_task="按依赖顺序完成任务",
            steps=[
                PlanStep(key="s-c", name="step-c", priority=30, depends_on=["s-a"], payload={}),
                PlanStep(key="s-a", name="step-a", priority=50, payload={}),
                PlanStep(key="s-b", name="step-b", priority=10, payload={}),
            ],
        )

    async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
        called_steps.append(step.name)
        return StepOutcome(status="ok", output={"step": step.name, "idx": step_idx})

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))
    assert updated.final_answer is not None
    assert updated.final_answer.status == "success"
    assert called_steps == ["step-b", "step-a", "step-c"]


def test_engine_should_fail_when_plan_dependency_missing() -> None:
    """计划引用不存在的依赖步骤时应在 plan 阶段失败。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=2, time_budget_ms=5000))
    state = build_initial_state("session_engine_invalid_plan")

    def plan_fn(_: AgentState) -> ExecutionPlan:
        return ExecutionPlan(
            global_task="测试非法依赖",
            steps=[PlanStep(key="s-a", name="step-a", depends_on=["missing"], payload={})],
        )

    async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
        return StepOutcome(status="ok", output={"step": step.name, "idx": step_idx})

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))
    assert updated.final_answer is not None
    assert updated.final_answer.status == "failed"
    assert any(e.error and e.error.error_code == "PLAN_INVALID" for e in updated.events if e.event_type == "error")


def test_engine_should_record_global_task_in_plan_events() -> None:
    """计划对象里的全局任务应进入事件，避免只剩步骤没有目标。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=2, time_budget_ms=5000))
    state = build_initial_state("session_engine_global_task")

    def plan_fn(_: AgentState) -> ExecutionPlan:
        return ExecutionPlan(
            global_task="为用户生成一份可执行的劳动仲裁行动方案",
            reason="初始化计划",
            steps=[
                PlanStep(key="s-a", name="collect-facts", kind="analysis", payload={}),
                PlanStep(key="s-b", name="draft-actions", kind="generation", payload={}),
            ],
        )

    async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
        return StepOutcome(status="ok", output={"step": step.name, "idx": step_idx})

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))
    assert any(
        e.event_type == "plan" and e.payload.get("global_task") == "为用户生成一份可执行的劳动仲裁行动方案"
        for e in updated.events
    )
    assert any(
        e.event_type == "finish" and e.payload.get("global_task") == "为用户生成一份可执行的劳动仲裁行动方案"
        for e in updated.events
    )


def test_engine_should_record_plan_governance_fields_in_events() -> None:
    """计划的成功标准、约束、风险和审计信息应进入事件。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=2, time_budget_ms=5000))
    state = build_initial_state("session_engine_plan_governance")

    def plan_fn(_: AgentState) -> ExecutionPlan:
        return ExecutionPlan(
            global_task="生成带风控约束的执行方案",
            success_criteria=["输出行动方案", "不遗漏关键证据清单"],
            constraints=["不能调用外部付费服务", "总步骤数不超过 2"],
            risk_level="high",
            audit=PlanAudit(created_by="planner", change_summary="初始化计划"),
            steps=[PlanStep(key="s-a", name="step-a", payload={})],
        )

    async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
        return StepOutcome(status="ok", output={"step": step.name, "idx": step_idx})

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))
    plan_event = next(event for event in updated.events if event.event_type == "plan")
    finish_event = next(event for event in updated.events if event.event_type == "finish")
    assert plan_event.payload["success_criteria"] == ["输出行动方案", "不遗漏关键证据清单"]
    assert plan_event.payload["constraints"] == ["不能调用外部付费服务", "总步骤数不超过 2"]
    assert plan_event.payload["risk_level"] == "high"
    assert plan_event.payload["plan_audit"]["created_by"] == "planner"
    assert finish_event.payload["risk_level"] == "high"


def test_engine_should_record_replan_audit_fields() -> None:
    """重规划后应记录上一个修订号和触发步骤，便于回放和审计。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=4, time_budget_ms=5000, max_replans=1))
    state = build_initial_state("session_engine_replan_audit")

    def plan_fn(_: AgentState) -> ExecutionPlan:
        return ExecutionPlan(
            global_task="先执行，再按风险重规划",
            success_criteria=["完成最终步骤"],
            constraints=["禁止跳过审计记录"],
            risk_level="medium",
            audit=PlanAudit(created_by="planner", change_summary="初始化计划"),
            steps=[
                PlanStep(key="s-a", name="step-a", payload={}),
                PlanStep(key="s-b", name="step-b", payload={}),
            ],
        )

    async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
        if step.name == "step-a":
            return StepOutcome(
                status="error",
                output={"need_replan": True},
                error=ErrorInfo(error_code="NEED_REPLAN", error_message="需要重规划", retryable=False),
            )
        return StepOutcome(status="ok", output={"step": step.name, "idx": step_idx})

    async def reflect_fn(_: AgentState, step: PlanStep, step_idx: int, outcome: StepOutcome) -> ReflectDecision:
        if step.name == "step-a" and outcome.status == "error":
            return ReflectDecision(
                action="replan",
                reason="首步失败，需要调整计划",
                replacement_plan=ExecutionPlan(
                    origin="replan",
                    risk_level="high",
                    audit=PlanAudit(created_by="policy"),
                    steps=[PlanStep(key="s-c", name="step-c", payload={})],
                ),
            )
        return ReflectDecision(action="continue", reason="继续执行")

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn, reflect_fn=reflect_fn))
    replan_event = next(
        event for event in updated.events if event.event_type == "plan" and event.payload.get("phase") == "replan"
    )
    finish_event = next(event for event in updated.events if event.event_type == "finish")
    assert replan_event.payload["plan_revision"] == 2
    assert replan_event.payload["risk_level"] == "high"
    assert replan_event.payload["plan_audit"]["previous_revision"] == 1
    assert replan_event.payload["plan_audit"]["triggered_by_step_key"] == "s-a"
    assert replan_event.payload["plan_audit"]["created_by"] == "policy"
    assert finish_event.payload["plan_audit"]["triggered_by_step_name"] == "step-a"


def test_engine_should_inherit_risk_and_audit_creator_when_replan_omits_them() -> None:
    """重规划未显式声明治理字段时，不应被默认值静默覆盖。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=4, time_budget_ms=5000, max_replans=1))
    state = build_initial_state("session_engine_replan_inherit")

    def plan_fn(_: AgentState) -> ExecutionPlan:
        return ExecutionPlan(
            global_task="保持原风险级别和审计来源",
            risk_level="critical",
            audit=PlanAudit(created_by="human", change_summary="人工确认后的计划"),
            steps=[
                PlanStep(key="s-a", name="step-a", payload={}),
                PlanStep(key="s-b", name="step-b", payload={}),
            ],
        )

    async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
        if step.name == "step-a":
            return StepOutcome(
                status="error",
                output={"need_replan": True},
                error=ErrorInfo(error_code="NEED_REPLAN", error_message="需要重规划", retryable=False),
            )
        return StepOutcome(status="ok", output={"step": step.name, "idx": step_idx})

    async def reflect_fn(_: AgentState, step: PlanStep, step_idx: int, outcome: StepOutcome) -> ReflectDecision:
        if step.name == "step-a" and outcome.status == "error":
            return ReflectDecision(
                action="replan",
                reason="调整步骤但不改治理字段",
                replacement_plan=ExecutionPlan(
                    origin="replan",
                    steps=[PlanStep(key="s-c", name="step-c", payload={})],
                ),
            )
        return ReflectDecision(action="continue", reason="继续执行")

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn, reflect_fn=reflect_fn))
    replan_event = next(
        event for event in updated.events if event.event_type == "plan" and event.payload.get("phase") == "replan"
    )
    assert replan_event.payload["risk_level"] == "critical"
    assert replan_event.payload["plan_audit"]["created_by"] == "human"


def test_engine_should_replan_remaining_steps() -> None:
    """reflect 应能把剩余步骤替换成新计划。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=5, time_budget_ms=5000, max_replans=2))
    state = build_initial_state("session_engine_replan")
    called_steps: list[str] = []

    def plan_fn(_: AgentState) -> ExecutionPlan:
        return ExecutionPlan(
            global_task="先完成初始任务，再根据结果重规划",
            steps=[
                PlanStep(key="s-a", name="step-a", kind="analysis", payload={}),
                PlanStep(key="s-b", name="step-b", kind="analysis", payload={}),
            ],
        )

    async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
        called_steps.append(step.name)
        if step.name == "step-a":
            return StepOutcome(status="error", output={"need_replan": True}, error=ErrorInfo(error_code="NEED_REPLAN", error_message="需要换计划", retryable=False))
        return StepOutcome(status="ok", output={"step": step.name, "idx": step_idx})

    async def reflect_fn(_: AgentState, step: PlanStep, step_idx: int, outcome: StepOutcome) -> ReflectDecision:
        if step.name == "step-a" and outcome.status == "error":
            return ReflectDecision(
                action="replan",
                reason="首步失败，替换剩余计划",
                replacement_plan=ExecutionPlan(
                    origin="replan",
                    steps=[
                        PlanStep(key="s-c", name="step-c", kind="recovery", payload={}),
                        PlanStep(key="s-d", name="step-d", kind="generation", payload={}),
                    ],
                ),
            )
        return ReflectDecision(action="continue", reason="继续执行")

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn, reflect_fn=reflect_fn))
    assert called_steps == ["step-a", "step-c", "step-d"]
    assert updated.final_answer is not None
    assert updated.final_answer.status == "success"
    assert updated.final_answer.output["replan_count"] == 1
    assert any(e.event_type == "plan" and e.payload.get("phase") == "replan" for e in updated.events)


def test_engine_should_fail_when_replan_limit_reached() -> None:
    """重规划超过上限时应明确失败，而不是无限改计划。"""

    engine = EngineLoop(limits=EngineLimits(max_steps=4, time_budget_ms=5000, max_replans=0))
    state = build_initial_state("session_engine_replan_limit")

    def plan_fn(_: AgentState) -> ExecutionPlan:
        return ExecutionPlan(
            global_task="测试重规划上限",
            steps=[PlanStep(key="s-a", name="step-a", kind="analysis", payload={})],
        )

    async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
        return StepOutcome(status="error", output={}, error=ErrorInfo(error_code="FAIL", error_message="fail", retryable=False))

    async def reflect_fn(_: AgentState, step: PlanStep, step_idx: int, outcome: StepOutcome) -> ReflectDecision:
        return ReflectDecision(
            action="replan",
            reason="尝试重规划",
            replacement_plan=ExecutionPlan(
                origin="replan",
                steps=[PlanStep(key="s-b", name="step-b", kind="recovery", payload={})],
            ),
        )

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn, reflect_fn=reflect_fn))
    assert updated.final_answer is not None
    assert updated.final_answer.status == "failed"
    assert any(e.error and e.error.error_code == "REPLAN_LIMIT_REACHED" for e in updated.events if e.event_type == "error")


def test_engine_should_allow_attempt_stage_injection() -> None:
    """单步 attempt 阶段应允许插入额外观测逻辑。"""

    def attempt_stage_customizer(stages: list[EngineStage]) -> list[EngineStage]:
        observe_index = next(index for index, stage in enumerate(stages) if stage.name == "observe")

        async def mark_attempt(context: EnginePipelineContext) -> None:
            context.append_event(
                event_type="state_update",
                step_id=context.current_step_id,
                payload={
                    "phase": "attempt_marker",
                    "step_key": context.current_step.key if context.current_step is not None else "",
                    "attempt": context.current_attempt,
                },
            )

        return stages[: observe_index + 1] + [EngineStage(name="attempt_marker", handler=mark_attempt)] + stages[observe_index + 1 :]

    engine = EngineLoop(
        limits=EngineLimits(max_steps=2, time_budget_ms=5000),
        attempt_stage_customizer=attempt_stage_customizer,
    )
    state = build_initial_state("session_engine_attempt_extension")

    def plan_fn(_: AgentState) -> list[dict]:
        return [{"id": "s-a", "name": "step-a"}]

    async def act_fn(_: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
        return StepOutcome(status="ok", output={"step": step.name, "idx": step_idx})

    updated = asyncio.run(engine.arun(state, plan_fn=plan_fn, act_fn=act_fn))
    assert updated.final_answer is not None
    assert updated.final_answer.status == "success"
    assert any(e.payload.get("phase") == "attempt_marker" for e in updated.events if e.event_type == "state_update")


