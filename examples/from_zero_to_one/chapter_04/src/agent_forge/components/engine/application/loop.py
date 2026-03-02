"""Engine(loop) 组件（asyncio 生产导向版）。

核心目标：
1. 主循环异步化：plan -> act -> observe -> reflect -> update -> finish
2. 恢复一致性：stable step key 跳过已完成步骤
3. 预算控制：max_steps / time_budget / step_timeout / retry
4. 可扩展执行：act_executor 可注入；默认执行器支持协程与同步函数
5. 性能语义：共享线程池、并发背压、attempt 指标、trace 输出摘要化
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import monotonic
from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel, Field

from agent_forge.components.protocol import AgentState, ErrorInfo, ExecutionEvent, FinalAnswer


class EngineLimits(BaseModel):
    """执行限制。"""

    max_steps: int = Field(default=8, ge=1, description="最大执行步数（只统计实际执行步）")
    time_budget_ms: int = Field(default=3000, ge=1, description="run 级时间预算（毫秒）")
    step_timeout_ms: int = Field(default=1200, ge=1, description="单步超时（毫秒）")
    max_retry_per_step: int = Field(default=1, ge=0, description="单步最大重试次数")
    executor_max_workers: int = Field(default=8, ge=1, description="共享执行池线程数")
    max_inflight_acts: int = Field(default=32, ge=1, description="同时在途 act 上限（背压）")
    trace_output_preview_chars: int = Field(default=240, ge=32, description="trace 输出预览最大字符数")


class StepOutcome(BaseModel):
    """单步执行结果。"""

    status: Literal["ok", "error"] = Field(..., description="步骤状态")
    output: dict[str, Any] = Field(default_factory=dict, description="步骤输出")
    error: ErrorInfo | None = Field(default=None, description="错误信息")


class ReflectDecision(BaseModel):
    """反思决策结果。"""

    action: Literal["continue", "retry", "abort"] = Field(..., description="反思动作")
    reason: str = Field(default="", description="决策原因")


class RunContext(BaseModel):
    """运行隔离与版本上下文。"""

    tenant_id: str | None = Field(default=None, description="租户 ID（可选）")
    user_id: str | None = Field(default=None, description="用户 ID（可选）")
    config_version: str = Field(default="v1", description="配置版本")
    model_version: str = Field(default="unset", description="模型版本")
    tool_version: str = Field(default="unset", description="工具版本")
    policy_version: str = Field(default="v1", description="策略版本")


class PlanStep(BaseModel):
    """标准化步骤对象。"""

    key: str = Field(..., min_length=1, description="稳定步骤键")
    name: str = Field(..., min_length=1, description="步骤名称")
    payload: dict[str, Any] = Field(default_factory=dict, description="步骤扩展数据")


PlanFn = Callable[[AgentState], list[str | dict[str, Any] | PlanStep]]
ActFn = Callable[[AgentState, PlanStep, int], StepOutcome | Awaitable[StepOutcome]]
ReflectFn = Callable[
    [AgentState, PlanStep, int, StepOutcome], ReflectDecision | Awaitable[ReflectDecision]
]
ActExecutor = Callable[[ActFn, AgentState, PlanStep, int, int], Awaitable[StepOutcome]]


@dataclass
class _RunStats:
    """内部运行统计。"""

    total_planned_steps: int = 0
    executed_steps: int = 0
    success_steps: int = 0
    failed_steps: int = 0
    reflected_retry_count: int = 0
    skipped_steps: int = 0
    attempt_count: int = 0
    stop_reason: str = "finished"


class EngineLoop:
    """生产导向 Engine 循环实现（asyncio）。"""

    def __init__(
        self,
        limits: EngineLimits | None = None,
        now_ms: Callable[[], int] | None = None,
        act_executor: ActExecutor | None = None,
    ) -> None:
        self.limits = limits or EngineLimits()
        self._now_ms = now_ms or (lambda: int(monotonic() * 1000))
        self._executor = ThreadPoolExecutor(max_workers=self.limits.executor_max_workers)
        self._inflight_guard = asyncio.Semaphore(self.limits.max_inflight_acts)
        self._act_executor = act_executor or self._default_act_executor

    def close(self) -> None:
        """释放共享执行池资源。"""

        self._executor.shutdown(wait=False, cancel_futures=True)

    async def arun(
        self,
        state: AgentState,
        plan_fn: PlanFn,
        act_fn: ActFn,
        reflect_fn: ReflectFn | None = None,
        context: RunContext | None = None,
    ) -> AgentState:
        """异步执行一轮完整 loop，并返回更新后的 state。"""

        context = context or RunContext()
        reflect_fn = reflect_fn or self._default_reflect
        started_at = self._now_ms()
        stats = _RunStats()
        # 1. 初始化阶段：标准化输入并记录起始状态
        plan_steps = self._normalize_plan_steps(plan_fn(state))
        stats.total_planned_steps = len(plan_steps)
        completed_step_keys = self._completed_step_keys(state)

        # 2. plan 事件落盘：无论成功与否先记录计划
        self._append_event(
            state=state,
            event_type="plan",
            step_id="step_plan",
            payload={
                "plan_steps": [{"key": s.key, "name": s.name} for s in plan_steps],
                "plan_count": len(plan_steps),
                "context": context.model_dump(),
            },
        )

        # 3. 遍历步骤：按顺序执行标准化后的计划步骤
        for idx, step in enumerate(plan_steps, start=1):
            step_id = f"step_{idx}"

            # 3.1 尝试跳过已完成步骤 (resume_skip)
            if step.key in completed_step_keys:
                stats.skipped_steps += 1
                self._append_event(
                    state=state,
                    event_type="state_update",
                    step_id=step_id,
                    payload={"phase": "resume_skip", "step_key": step.key, "step_name": step.name, "attempt": 0},
                )
                continue

            # 3.2 检查执行步数是否超限 (max_steps 预算保护)
            stats.executed_steps += 1
            if stats.executed_steps > self.limits.max_steps:
                stats.stop_reason = "max_steps_reached"
                self._append_event(
                    state=state,
                    event_type="error",
                    step_id=step_id,
                    payload={"step_key": step.key, "step_name": step.name, "attempt": 0},
                    error=ErrorInfo(
                        error_code="MAX_STEPS_REACHED",
                        error_message="Engine 达到最大执行步数限制",
                        retryable=False,
                    ),
                )
                break

            # 4. 单步执行尝试循环 (attempt loop)
            attempt = 0
            while True:
                # 4.1 检查系统总时间预算 (防止因无限重试导致全局超时)
                if self._exceed_time_budget(started_at):
                    stats.stop_reason = "time_budget_exceeded"
                    self._append_event(
                        state=state,
                        event_type="error",
                        step_id=step_id,
                        payload={"step_key": step.key, "step_name": step.name, "attempt": attempt},
                        error=ErrorInfo(
                            error_code="TIME_BUDGET_EXCEEDED",
                            error_message="Engine 超出时间预算",
                            retryable=False,
                        ),
                    )
                    break

                # 4.2 记录 act 开始状态
                stats.attempt_count += 1
                self._append_event(
                    state=state,
                    event_type="state_update",
                    step_id=step_id,
                    payload={"phase": "act_start", "step_key": step.key, "step_name": step.name, "attempt": attempt},
                )

                # 4.3 调用底层执行器并获取执行结果 (act & observe)
                outcome = await self._act_executor(act_fn, state, step, idx, self.limits.step_timeout_ms)
                summary, out_hash = self._summarize_output(outcome.output)
                self._append_event(
                    state=state,
                    event_type="state_update",
                    step_id=step_id,
                    payload={
                        "phase": "observe",
                        "step_key": step.key,
                        "step_name": step.name,
                        "attempt": attempt,
                        "status": outcome.status,
                        "output_summary": summary,
                        "output_hash": out_hash,
                    },
                )

                # 4.4 根据结果进行反思判断 (reflect)
                decision = await self._maybe_await(reflect_fn(state, step, idx, outcome))
                self._append_event(
                    state=state,
                    event_type="state_update",
                    step_id=step_id,
                    payload={
                        "phase": "reflect",
                        "step_key": step.key,
                        "step_name": step.name,
                        "attempt": attempt,
                        "decision": decision.action,
                        "reason": decision.reason,
                    },
                )

                # 5. 成功提交或失败处理
                # 5.1 成功提交并落盘 update 事件
                if outcome.status == "ok" and decision.action == "continue":
                    stats.success_steps += 1
                    self._append_event(
                        state=state,
                        event_type="state_update",
                        step_id=step_id,
                        payload={
                            "phase": "update",
                            "step_key": step.key,
                            "step_name": step.name,
                            "attempt": attempt,
                            "output_summary": summary,
                            "output_hash": out_hash,
                        },
                    )
                    completed_step_keys.add(step.key)
                    break

                # 5.2 触发重试逻辑
                if decision.action == "retry" and attempt < self.limits.max_retry_per_step:
                    attempt += 1
                    stats.reflected_retry_count += 1
                    continue

                # 5.3 不可恢复的失败，终止当前步骤
                stats.failed_steps += 1
                stats.stop_reason = "step_failed"
                self._append_event(
                    state=state,
                    event_type="error",
                    step_id=step_id,
                    payload={
                        "step_key": step.key,
                        "step_name": step.name,
                        "attempt": attempt,
                        "output_summary": summary,
                        "output_hash": out_hash,
                    },
                    error=outcome.error
                    or ErrorInfo(error_code="STEP_FAILED", error_message="步骤执行失败", retryable=False),
                )
                break

            
            # 若由于时间预算超限或步骤崩溃而退出 attempt 循环，将直接跳出主计划循环
            if stats.stop_reason in {"time_budget_exceeded", "step_failed"}:
                break

        # 6. finish 收尾：整合运行统计信息并产生 FinalAnswer
        self._append_event(
            state=state,
            event_type="finish",
            step_id="step_finish",
            payload={
                "context": context.model_dump(),
                "total_planned_steps": stats.total_planned_steps,
                "executed_steps": stats.executed_steps,
                "success_steps": stats.success_steps,
                "failed_steps": stats.failed_steps,
                "reflected_retry_count": stats.reflected_retry_count,
                "skipped_steps": stats.skipped_steps,
                "attempt_count": stats.attempt_count,
                "completed_step_keys": sorted(list(completed_step_keys)),
                "stop_reason": stats.stop_reason,
            },
        )
        state.final_answer = self._build_final_answer(stats, started_at)
        return state

    def run(
        self,
        state: AgentState,
        plan_fn: PlanFn,
        act_fn: ActFn,
        reflect_fn: ReflectFn | None = None,
        context: RunContext | None = None,
    ) -> AgentState:
        """同步包装器。

        注意：
        - 如果调用方已有事件循环，请直接使用 `await arun(...)`。
        """

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(state, plan_fn, act_fn, reflect_fn, context))
        raise RuntimeError("检测到正在运行的事件循环，请改用 await arun(...)")

    async def _default_act_executor(
        self, act_fn: ActFn, state: AgentState, step: PlanStep, idx: int, timeout_ms: int
    ) -> StepOutcome:
        """默认 act 执行器（共享线程池 + 背压 + asyncio 超时）。"""

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
        """兼容同步/异步反思函数。"""

        if inspect.isawaitable(value):
            return await value
        return value

    @staticmethod
    def _default_reflect(_: AgentState, __: PlanStep, ___: int, outcome: StepOutcome) -> ReflectDecision:
        """默认反思策略：成功继续，失败按 retryable 决策。"""

        if outcome.status == "ok":
            return ReflectDecision(action="continue", reason="步骤执行成功")
        if outcome.error and outcome.error.retryable:
            return ReflectDecision(action="retry", reason="错误可重试")
        return ReflectDecision(action="abort", reason="错误不可重试")

    def _append_event(
        self,
        state: AgentState,
        event_type: Literal["plan", "tool_call", "tool_result", "state_update", "finish", "error"],
        step_id: str,
        payload: dict[str, Any],
        error: ErrorInfo | None = None,
    ) -> None:
        """统一写事件，确保 trace 结构一致。"""

        state.events.append(
            ExecutionEvent(
                trace_id=state.trace_id,
                run_id=state.run_id,
                step_id=step_id,
                event_type=event_type,
                payload=payload,
                error=error,
            )
        )

    def _build_final_answer(self, stats: _RunStats, started_at: int) -> FinalAnswer:
        """构造通用最终输出。"""

        status: Literal["success", "partial", "failed"] = "success"
        if stats.failed_steps > 0:
            status = "failed"
        elif stats.stop_reason != "finished":
            status = "partial"

        elapsed_ms = max(1, self._now_ms() - started_at)
        steps_per_second = round((stats.executed_steps / elapsed_ms) * 1000, 3)

        return FinalAnswer(
            status=status,
            summary=f"Engine 执行结束：{stats.stop_reason}",
            output={
                "total_planned_steps": stats.total_planned_steps,
                "executed_steps": stats.executed_steps,
                "success_steps": stats.success_steps,
                "failed_steps": stats.failed_steps,
                "reflected_retry_count": stats.reflected_retry_count,
                "skipped_steps": stats.skipped_steps,
                "attempt_count": stats.attempt_count,
                "stop_reason": stats.stop_reason,
                "elapsed_ms": elapsed_ms,
                "steps_per_second": steps_per_second,
            },
            artifacts=[{"type": "engine_stats", "name": "loop_result"}],
            references=[],
        )

    def _completed_step_keys(self, state: AgentState) -> set[str]:
        """提取历史已完成步骤键（优先读 finish 索引）。"""

        for event in reversed(state.events):
            if event.event_type != "finish":
                continue
            keys = event.payload.get("completed_step_keys")
            if isinstance(keys, list):
                parsed = {k for k in keys if isinstance(k, str) and k}
                if parsed:
                    return parsed

        completed: set[str] = set()
        for event in state.events:
            if event.event_type != "state_update":
                continue
            if event.payload.get("phase") != "update":
                continue
            step_key = event.payload.get("step_key")
            if isinstance(step_key, str) and step_key:
                completed.add(step_key)
        return completed

    def _exceed_time_budget(self, started_at: int) -> bool:
        """检查 run 级时间预算。"""

        return (self._now_ms() - started_at) > self.limits.time_budget_ms

    def _summarize_output(self, output: dict[str, Any]) -> tuple[str, str]:
        """对步骤输出做摘要，控制 trace 体积。"""

        raw = json.dumps(output, ensure_ascii=False, sort_keys=True)
        out_hash = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
        preview = raw[: self.limits.trace_output_preview_chars]
        summary = f"len={len(raw)},preview={preview}"
        return summary, out_hash

    @staticmethod
    def _normalize_plan_steps(raw_steps: list[str | dict[str, Any] | PlanStep]) -> list[PlanStep]:
        """标准化 plan 步骤。"""

        normalized: list[PlanStep] = []
        for item in raw_steps:
            if isinstance(item, PlanStep):
                normalized.append(item)
                continue
            if isinstance(item, str):
                key = EngineLoop._stable_hash({"name": item})
                normalized.append(PlanStep(key=key, name=item, payload={}))
                continue
            step_id = item.get("id") if isinstance(item.get("id"), str) else ""
            step_name = item.get("name") if isinstance(item.get("name"), str) else "unnamed_step"
            payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
            if not step_id:
                step_id = EngineLoop._stable_hash({"name": step_name, "payload": payload})
            normalized.append(PlanStep(key=step_id, name=step_name, payload=payload))
        return normalized

    @staticmethod
    def _stable_hash(value: dict[str, Any]) -> str:
        """生成稳定哈希，用于步骤键。"""

        raw = json.dumps(value, sort_keys=True, ensure_ascii=False)
        return f"step_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"

