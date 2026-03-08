"""Engine 运行时 facade。"""

from __future__ import annotations

import asyncio
import inspect
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, Callable, Literal

from agent_forge.components.engine.application.context import (
    EnginePipelineContext,
    EngineStage,
    RunStats,
    StageCustomizer,
)
from agent_forge.components.engine.application.helpers import (
    build_final_answer,
    build_replanned_plan,
    completed_step_keys,
    default_now_ms,
    exceed_time_budget,
    normalize_execution_plan,
    schedule_execution_plan,
    summarize_output,
)
from agent_forge.components.engine.domain import (
    ActExecutor,
    ActFn,
    EngineEventListener,
    EngineLimits,
    ExecutionPlan,
    PlanFn,
    PlanStep,
    ReflectDecision,
    ReflectFn,
    RunContext,
    StepOutcome,
)
from agent_forge.components.protocol import AgentState, ErrorInfo, ExecutionEvent
from agent_forge.support.logging import get_logger

logger = get_logger(__name__)


class EngineLoop:
    """生产导向 Engine 循环实现（阶段可插拔 facade）。

    Args:
        limits: 执行限制配置。
        now_ms: 当前时间函数。
        act_executor: 自定义执行器。
        event_listener: 事件监听器。
        pipeline_customizer: 顶层阶段定制器。
        attempt_stage_customizer: 单步尝试阶段定制器。

    Returns:
        EngineLoop: 可运行的 Engine facade。
    """

    def __init__(
        self,
        limits: EngineLimits | None = None,
        now_ms: Callable[[], int] | None = None,
        act_executor: ActExecutor | None = None,
        event_listener: EngineEventListener | None = None,
        pipeline_customizer: StageCustomizer | None = None,
        attempt_stage_customizer: StageCustomizer | None = None,
    ) -> None:
        self.limits = limits or EngineLimits()
        self._now_ms = now_ms or default_now_ms
        self._executor = ThreadPoolExecutor(max_workers=self.limits.executor_max_workers)
        self._inflight_guard = asyncio.Semaphore(self.limits.max_inflight_acts)
        self._act_executor = act_executor or self._default_act_executor
        self._event_listener = event_listener
        self._pipeline_customizer = pipeline_customizer
        self._attempt_stage_customizer = attempt_stage_customizer

    def close(self) -> None:
        """释放共享执行池资源。

        Returns:
            None
        """

        self._executor.shutdown(wait=False, cancel_futures=True)

    async def arun(
        self,
        state: AgentState,
        plan_fn: PlanFn,
        act_fn: ActFn,
        reflect_fn: ReflectFn | None = None,
        context: RunContext | None = None,
    ) -> AgentState:
        """异步执行一轮完整 loop。

        Args:
            state: 当前状态对象。
            plan_fn: 计划函数。
            act_fn: 执行函数。
            reflect_fn: 反思函数。
            context: 运行上下文。

        Returns:
            AgentState: 更新后的状态对象。
        """

        pipeline_context = EnginePipelineContext(
            state=state,
            run_context=context or RunContext(),
            plan_fn=plan_fn,
            act_fn=act_fn,
            reflect_fn=reflect_fn or self._default_reflect,
            started_at_ms=self._now_ms(),
            stats=RunStats(),
            event_writer=self._append_event,
            limits=self.limits,
        )

        for stage in self._build_pipeline():
            await self._run_stage(stage, pipeline_context)

        if not pipeline_context.finish_emitted:
            await self._stage_finish(pipeline_context)

        return pipeline_context.state

    def run(
        self,
        state: AgentState,
        plan_fn: PlanFn,
        act_fn: ActFn,
        reflect_fn: ReflectFn | None = None,
        context: RunContext | None = None,
    ) -> AgentState:
        """同步包装器。

        Args:
            state: 当前状态对象。
            plan_fn: 计划函数。
            act_fn: 执行函数。
            reflect_fn: 反思函数。
            context: 运行上下文。

        Returns:
            AgentState: 更新后的状态对象。

        Raises:
            RuntimeError: 当前线程已有事件循环时，要求调用方改用 `await arun(...)`。
        """

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(state, plan_fn, act_fn, reflect_fn, context))
        raise RuntimeError("检测到正在运行的事件循环，请改用 await arun(...)")

    def _build_pipeline(self) -> list[EngineStage]:
        """构建顶层阶段 pipeline。

        Returns:
            list[EngineStage]: 顶层阶段列表。
        """

        stages = [
            EngineStage(name="plan", handler=self._stage_plan),
            EngineStage(name="execute_steps", handler=self._stage_execute_steps),
            EngineStage(name="finish", handler=self._stage_finish),
        ]
        if self._pipeline_customizer is not None:
            stages = self._pipeline_customizer(stages)
        return stages

    def _build_attempt_pipeline(self) -> list[EngineStage]:
        """构建单步尝试阶段 pipeline。

        Returns:
            list[EngineStage]: 单步尝试阶段列表。
        """

        stages = [
            EngineStage(name="time_budget_guard", handler=self._attempt_time_budget_guard),
            EngineStage(name="act_start", handler=self._attempt_act_start),
            EngineStage(name="act", handler=self._attempt_act),
            EngineStage(name="observe", handler=self._attempt_observe),
            EngineStage(name="reflect", handler=self._attempt_reflect),
            EngineStage(name="decide", handler=self._attempt_decide),
        ]
        if self._attempt_stage_customizer is not None:
            stages = self._attempt_stage_customizer(stages)
        return stages

    async def _run_stage(self, stage: EngineStage, context: EnginePipelineContext) -> None:
        """统一执行阶段。

        Args:
            stage: 当前阶段。
            context: pipeline 共享上下文。

        Returns:
            None
        """

        result = stage.handler(context)
        if inspect.isawaitable(result):
            await result

    async def _stage_plan(self, context: EnginePipelineContext) -> None:
        """执行 plan 阶段。

        Args:
            context: pipeline 共享上下文。

        Returns:
            None
        """

        context.completed_step_keys = completed_step_keys(context.state)
        raw_plan = normalize_execution_plan(context.plan_fn(context.state))
        try:
            plan = schedule_execution_plan(raw_plan, context.completed_step_keys)
        except ValueError as exc:
            context.stats.failed_steps += 1
            context.request_stop("plan_invalid")
            context.append_event(
                event_type="error",
                step_id="step_plan",
                payload={"phase": "plan"},
                error=ErrorInfo(
                    error_code="PLAN_INVALID",
                    error_message=str(exc),
                    retryable=False,
                ),
            )
            return
        context.apply_plan(plan)
        context.append_event(
            event_type="plan",
            step_id="step_plan",
            payload={
                "plan_id": plan.plan_id,
                "plan_revision": plan.revision,
                "plan_origin": plan.origin,
                "plan_reason": plan.reason,
                "global_task": plan.global_task,
                "success_criteria": plan.success_criteria,
                "constraints": plan.constraints,
                "risk_level": plan.risk_level,
                "plan_audit": plan.audit.model_dump(),
                "plan_metadata": plan.metadata,
                "plan_steps": [
                    {
                        "key": step.key,
                        "name": step.name,
                        "kind": step.kind,
                        "depends_on": step.depends_on,
                        "priority": step.priority,
                    }
                    for step in plan.steps
                ],
                "plan_count": len(plan.steps),
                "context": context.run_context.model_dump(),
            },
        )

    async def _stage_execute_steps(self, context: EnginePipelineContext) -> None:
        """执行步骤阶段。

        Args:
            context: pipeline 共享上下文。

        Returns:
            None
        """

        step_index = 1
        while step_index <= len(context.plan_steps):
            step = context.plan_steps[step_index - 1]
            context.prepare_step(step, step_index)

            if step.key in context.completed_step_keys:
                context.stats.skipped_steps += 1
                context.append_event(
                    event_type="state_update",
                    step_id=context.current_step_id,
                    payload={
                        "phase": "resume_skip",
                        "step_key": step.key,
                        "step_name": step.name,
                        "attempt": 0,
                    },
                )
                step_index += 1
                continue

            context.stats.executed_steps += 1
            if context.stats.executed_steps > self.limits.max_steps:
                context.request_stop("max_steps_reached")
                context.append_event(
                    event_type="error",
                    step_id=context.current_step_id,
                    payload={"step_key": step.key, "step_name": step.name, "attempt": 0},
                    error=ErrorInfo(
                        error_code="MAX_STEPS_REACHED",
                        error_message="Engine 达到最大执行步数限制",
                        retryable=False,
                    ),
                )
                break

            attempt = 0
            while True:
                context.prepare_attempt(attempt)
                for stage in self._build_attempt_pipeline():
                    await self._run_stage(stage, context)
                    if (
                        context.stop_requested
                        or context.retry_requested
                        or context.replan_requested
                        or context.step_completed
                        or context.step_terminal
                    ):
                        break

                if context.step_completed:
                    break

                if context.retry_requested:
                    attempt += 1
                    context.stats.reflected_retry_count += 1
                    continue

                if context.replan_requested:
                    break

                break

            if context.stop_requested:
                break

            if context.replan_requested:
                context.replan_requested = False
                continue

            step_index += 1

    async def _stage_finish(self, context: EnginePipelineContext) -> None:
        """执行 finish 阶段。

        Args:
            context: pipeline 共享上下文。

        Returns:
            None
        """

        context.append_event(
            event_type="finish",
            step_id="step_finish",
            payload={
                "context": context.run_context.model_dump(),
                "total_planned_steps": context.stats.total_planned_steps,
                "executed_steps": context.stats.executed_steps,
                "success_steps": context.stats.success_steps,
                "failed_steps": context.stats.failed_steps,
                "reflected_retry_count": context.stats.reflected_retry_count,
                "replan_count": context.stats.replan_count,
                "skipped_steps": context.stats.skipped_steps,
                "attempt_count": context.stats.attempt_count,
                "completed_step_keys": sorted(list(context.completed_step_keys)),
                "stop_reason": context.stats.stop_reason,
                "plan_id": context.current_plan.plan_id if context.current_plan is not None else "",
                "plan_revision": context.current_plan.revision if context.current_plan is not None else 0,
                "plan_origin": context.current_plan.origin if context.current_plan is not None else "",
                "global_task": context.current_plan.global_task if context.current_plan is not None else "",
                "success_criteria": context.current_plan.success_criteria if context.current_plan is not None else [],
                "constraints": context.current_plan.constraints if context.current_plan is not None else [],
                "risk_level": context.current_plan.risk_level if context.current_plan is not None else "",
                "plan_audit": context.current_plan.audit.model_dump() if context.current_plan is not None else {},
            },
        )
        context.state.final_answer = build_final_answer(
            context.stats,
            context.started_at_ms,
            self._now_ms(),
        )
        context.finish_emitted = True

    async def _attempt_time_budget_guard(self, context: EnginePipelineContext) -> None:
        """执行 run 级时间预算检查。

        Args:
            context: pipeline 共享上下文。

        Returns:
            None
        """

        if not exceed_time_budget(context.started_at_ms, self.limits.time_budget_ms, self._now_ms()):
            return

        context.request_stop("time_budget_exceeded")
        context.step_terminal = True
        context.append_event(
            event_type="error",
            step_id=context.current_step_id,
            payload={
                "step_key": context.current_step_key(),
                "step_name": context.current_step_name(),
                "attempt": context.current_attempt,
            },
            error=ErrorInfo(
                error_code="TIME_BUDGET_EXCEEDED",
                error_message="Engine 超出时间预算",
                retryable=False,
            ),
        )

    async def _attempt_act_start(self, context: EnginePipelineContext) -> None:
        """记录 act_start 阶段。

        Args:
            context: pipeline 共享上下文。

        Returns:
            None
        """

        context.stats.attempt_count += 1
        context.append_event(
            event_type="state_update",
            step_id=context.current_step_id,
            payload={
                "phase": "act_start",
                "step_key": context.current_step_key(),
                "step_name": context.current_step_name(),
                "attempt": context.current_attempt,
            },
        )

    async def _attempt_act(self, context: EnginePipelineContext) -> None:
        """执行 act 阶段。

        Args:
            context: pipeline 共享上下文。

        Returns:
            None
        """

        if context.current_step is None:
            return
        context.current_outcome = await self._act_executor(
            context.act_fn,
            context.state,
            context.current_step,
            context.current_step_index,
            context.current_step.timeout_ms or self.limits.step_timeout_ms,
        )

    async def _attempt_observe(self, context: EnginePipelineContext) -> None:
        """执行 observe 阶段。

        Args:
            context: pipeline 共享上下文。

        Returns:
            None
        """

        if context.current_step is None or context.current_outcome is None:
            return

        summary, output_hash = summarize_output(context.current_outcome.output, self.limits)
        context.current_output_summary = summary
        context.current_output_hash = output_hash
        context.append_event(
            event_type="state_update",
            step_id=context.current_step_id,
            payload={
                "phase": "observe",
                "step_key": context.current_step.key,
                "step_name": context.current_step.name,
                "attempt": context.current_attempt,
                "status": context.current_outcome.status,
                "output_summary": summary,
                "output_hash": output_hash,
            },
        )

    async def _attempt_reflect(self, context: EnginePipelineContext) -> None:
        """执行 reflect 阶段。

        Args:
            context: pipeline 共享上下文。

        Returns:
            None
        """

        if context.current_step is None or context.current_outcome is None:
            return

        context.current_decision = await self._maybe_await(
            context.reflect_fn(context.state, context.current_step, context.current_step_index, context.current_outcome)
        )
        context.append_event(
            event_type="state_update",
            step_id=context.current_step_id,
            payload={
                "phase": "reflect",
                "step_key": context.current_step.key,
                "step_name": context.current_step.name,
                "attempt": context.current_attempt,
                "decision": context.current_decision.action,
                "reason": context.current_decision.reason,
            },
        )

    async def _attempt_decide(self, context: EnginePipelineContext) -> None:
        """执行 decide 阶段。

        Args:
            context: pipeline 共享上下文。

        Returns:
            None
        """

        if context.current_step is None or context.current_outcome is None or context.current_decision is None:
            return

        if context.current_outcome.status == "ok" and context.current_decision.action == "continue":
            context.stats.success_steps += 1
            context.append_event(
                event_type="state_update",
                step_id=context.current_step_id,
                payload={
                    "phase": "update",
                    "step_key": context.current_step.key,
                    "step_name": context.current_step.name,
                    "attempt": context.current_attempt,
                    "output_summary": context.current_output_summary,
                    "output_hash": context.current_output_hash,
                },
            )
            context.completed_step_keys.add(context.current_step.key)
            context.step_completed = True
            return

        max_retry = (
            context.current_step.max_retry_per_step
            if context.current_step is not None and context.current_step.max_retry_per_step is not None
            else self.limits.max_retry_per_step
        )
        if context.current_decision.action == "retry" and context.current_attempt < max_retry:
            context.retry_requested = True
            return

        if context.current_decision.action == "replan":
            await self._apply_replan(context)
            return

        context.stats.failed_steps += 1
        context.request_stop("step_failed")
        context.step_terminal = True
        context.append_event(
            event_type="error",
            step_id=context.current_step_id,
            payload={
                "step_key": context.current_step.key,
                "step_name": context.current_step.name,
                "attempt": context.current_attempt,
                "output_summary": context.current_output_summary,
                "output_hash": context.current_output_hash,
            },
            error=context.current_outcome.error
            or ErrorInfo(error_code="STEP_FAILED", error_message="步骤执行失败", retryable=False),
        )

    async def _default_act_executor(
        self,
        act_fn: ActFn,
        state: AgentState,
        step: PlanStep,
        idx: int,
        timeout_ms: int,
    ) -> StepOutcome:
        """默认 act 执行器。

        Args:
            act_fn: 执行函数。
            state: 当前状态对象。
            step: 当前步骤。
            idx: 步骤序号。
            timeout_ms: 单步超时。

        Returns:
            StepOutcome: 标准化执行结果。
        """

        timeout_sec = max(0.001, timeout_ms / 1000.0)
        try:
            await asyncio.wait_for(self._inflight_guard.acquire(), timeout=timeout_sec)
        except asyncio.TimeoutError:
            return StepOutcome(
                status="error",
                output={},
                error=ErrorInfo(
                    error_code="ACT_BACKPRESSURE",
                    error_message="act 执行器达到并发上限",
                    retryable=True,
                ),
            )

        try:
            try:
                if inspect.iscoroutinefunction(act_fn):
                    return await asyncio.wait_for(act_fn(state, step, idx), timeout=timeout_sec)
                loop = asyncio.get_running_loop()
                return await asyncio.wait_for(
                    loop.run_in_executor(self._executor, lambda: act_fn(state, step, idx)),
                    timeout=timeout_sec,
                )
            except asyncio.TimeoutError:
                return StepOutcome(
                    status="error",
                    output={},
                    error=ErrorInfo(
                        error_code="STEP_TIMEOUT",
                        error_message="步骤执行超时",
                        retryable=True,
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                return StepOutcome(
                    status="error",
                    output={},
                    error=ErrorInfo(
                        error_code="ACT_EXECUTOR_EXCEPTION",
                        error_message=f"执行器异常: {exc}",
                        retryable=False,
                    ),
                )
        finally:
            self._inflight_guard.release()

    @staticmethod
    async def _maybe_await(value: ReflectDecision | Awaitable[ReflectDecision]) -> ReflectDecision:
        """兼容同步/异步反思函数。

        Args:
            value: 反思结果或 awaitable。

        Returns:
            ReflectDecision: 已解析的决策对象。
        """

        if inspect.isawaitable(value):
            return await value
        return value

    @staticmethod
    def _default_reflect(_: AgentState, __: PlanStep, ___: int, outcome: StepOutcome) -> ReflectDecision:
        """默认反思策略。

        Args:
            _: 当前状态对象。
            __: 当前步骤。
            ___: 步骤序号。
            outcome: 当前执行结果。

        Returns:
            ReflectDecision: 标准化决策对象。
        """

        if outcome.status == "ok":
            return ReflectDecision(action="continue", reason="步骤执行成功")
        if outcome.error and outcome.error.retryable:
            return ReflectDecision(action="retry", reason="错误可重试")
        return ReflectDecision(action="abort", reason="错误不可重试")

    async def _apply_replan(self, context: EnginePipelineContext) -> None:
        """执行重规划。

        Args:
            context: pipeline 共享上下文。

        Returns:
            None
        """

        if context.current_decision is None or context.current_step is None:
            return

        if context.stats.replan_count >= self.limits.max_replans:
            context.stats.failed_steps += 1
            context.request_stop("replan_limit_reached")
            context.step_terminal = True
            context.append_event(
                event_type="error",
                step_id=context.current_step_id,
                payload={
                    "step_key": context.current_step.key,
                    "step_name": context.current_step.name,
                    "attempt": context.current_attempt,
                },
                error=ErrorInfo(
                    error_code="REPLAN_LIMIT_REACHED",
                    error_message="重规划次数达到上限",
                    retryable=False,
                ),
            )
            return

        replacement = context.current_decision.replacement_plan
        if replacement is None:
            context.stats.failed_steps += 1
            context.request_stop("replan_missing_plan")
            context.step_terminal = True
            context.append_event(
                event_type="error",
                step_id=context.current_step_id,
                payload={
                    "step_key": context.current_step.key,
                    "step_name": context.current_step.name,
                    "attempt": context.current_attempt,
                },
                error=ErrorInfo(
                    error_code="REPLAN_PLAN_MISSING",
                    error_message="reflect 请求重规划，但未提供 replacement_plan",
                    retryable=False,
                ),
            )
            return

        replanned = build_replanned_plan(
            current_plan=context.current_plan,
            replacement_plan=replacement,
            reason=context.current_decision.reason,
            trigger_step=context.current_step,
        )
        try:
            scheduled_replanned = schedule_execution_plan(replanned, context.completed_step_keys)
        except ValueError as exc:
            context.stats.failed_steps += 1
            context.request_stop("replan_invalid")
            context.step_terminal = True
            context.append_event(
                event_type="error",
                step_id=context.current_step_id,
                payload={
                    "step_key": context.current_step.key,
                    "step_name": context.current_step.name,
                    "attempt": context.current_attempt,
                },
                error=ErrorInfo(
                    error_code="REPLAN_INVALID",
                    error_message=str(exc),
                    retryable=False,
                ),
            )
            return
        prefix = context.plan_steps[: context.current_step_index - 1]
        old_remaining = context.plan_steps[context.current_step_index :]
        if context.current_decision.plan_update_mode == "append_remaining":
            next_steps = prefix + old_remaining + scheduled_replanned.steps
        else:
            next_steps = prefix + scheduled_replanned.steps

        context.current_plan = scheduled_replanned
        context.replace_plan_steps(next_steps)
        context.stats.replan_count += 1
        context.replan_requested = True
        context.append_event(
            event_type="plan",
            step_id=f"{context.current_step_id}_replan",
            payload={
                "phase": "replan",
                "trigger_step_key": context.current_step.key,
                "trigger_step_name": context.current_step.name,
                "plan_id": context.current_plan.plan_id,
                "plan_revision": context.current_plan.revision,
                "plan_origin": context.current_plan.origin,
                "plan_reason": context.current_plan.reason,
                "global_task": context.current_plan.global_task,
                "success_criteria": context.current_plan.success_criteria,
                "constraints": context.current_plan.constraints,
                "risk_level": context.current_plan.risk_level,
                "plan_audit": context.current_plan.audit.model_dump(),
                "plan_count": len(context.current_plan.steps),
                "plan_steps": [
                    {
                        "key": step.key,
                        "name": step.name,
                        "kind": step.kind,
                        "depends_on": step.depends_on,
                        "priority": step.priority,
                    }
                    for step in context.current_plan.steps
                ],
            },
        )

    def _append_event(
        self,
        state: AgentState,
        event_type: Literal["plan", "tool_call", "tool_result", "state_update", "finish", "error"],
        step_id: str,
        payload: dict[str, object],
        error: ErrorInfo | None = None,
    ) -> None:
        """统一写事件。

        Args:
            state: 当前状态对象。
            event_type: 事件类型。
            step_id: 步骤 ID。
            payload: 事件载荷。
            error: 错误对象。

        Returns:
            None
        """

        event = ExecutionEvent(
            trace_id=state.trace_id,
            run_id=state.run_id,
            step_id=step_id,
            event_type=event_type,
            payload=payload,
            error=error,
        )
        state.events.append(event)
        if self._event_listener is not None:
            try:
                self._event_listener(event)
            except Exception as exc:  # noqa: BLE001
                logger.warning("engine event listener failed: %s", exc)
