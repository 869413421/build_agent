"""Engine(loop) 组件。

本模块只做一件事：消费 Protocol 状态并驱动执行循环。
当前版本先实现最小闭环：
1. plan -> 生成步骤列表
2. act -> 执行步骤动作
3. observe -> 记录事件
4. update -> 更新状态
5. finish -> 生成结构化最终输出
"""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from labor_agent.core.protocol import AgentState, ErrorInfo, ExecutionEvent, FinalAnswer


class EngineLimits(BaseModel):
    """执行限制。

    为什么必须有这两个限制：
    - max_steps：防止循环失控。
    - time_budget_ms：防止单次运行无限占用资源。
    """

    max_steps: int = Field(default=8, ge=1, description="最大执行步数")
    time_budget_ms: int = Field(default=3000, ge=1, description="时间预算（毫秒）")


class StepOutcome(BaseModel):
    """单步执行结果。"""

    status: Literal["ok", "error"] = Field(..., description="步骤状态")
    output: dict[str, Any] = Field(default_factory=dict, description="步骤输出")
    error: ErrorInfo | None = Field(default=None, description="错误信息")


PlanFn = Callable[[AgentState], list[str]]
ActFn = Callable[[AgentState, str, int], StepOutcome]


@dataclass
class _RunStats:
    """内部运行统计。

    该结构不写入协议，只用于组装最终输出。
    """

    total_steps: int = 0
    success_steps: int = 0
    failed_steps: int = 0
    stop_reason: str = "finished"


class EngineLoop:
    """最小可用执行循环。"""

    def __init__(self, limits: EngineLimits | None = None, now_ms: Callable[[], int] | None = None) -> None:
        self.limits = limits or EngineLimits()
        # 可注入时间函数，便于测试中做“确定性超时”验证。
        self._now_ms = now_ms or (lambda: int(monotonic() * 1000))

    def run(self, state: AgentState, plan_fn: PlanFn, act_fn: ActFn) -> AgentState:
        """执行一轮完整 loop，并返回更新后的 state。"""

        started_at = self._now_ms()
        stats = _RunStats()
        plan_steps = plan_fn(state)

        self._append_event(
            state=state,
            event_type="plan",
            step_id="step_plan",
            payload={"plan_steps": plan_steps, "plan_count": len(plan_steps)},
        )

        for idx, step in enumerate(plan_steps, start=1):
            stats.total_steps += 1

            if idx > self.limits.max_steps:
                stats.stop_reason = "max_steps_reached"
                self._append_event(
                    state=state,
                    event_type="error",
                    step_id=f"step_{idx}",
                    payload={"step": step},
                    error=ErrorInfo(
                        error_code="MAX_STEPS_REACHED",
                        error_message="Engine 达到最大执行步数限制",
                        retryable=False,
                    ),
                )
                break

            elapsed_ms = self._now_ms() - started_at
            if elapsed_ms > self.limits.time_budget_ms:
                stats.stop_reason = "time_budget_exceeded"
                self._append_event(
                    state=state,
                    event_type="error",
                    step_id=f"step_{idx}",
                    payload={"step": step, "elapsed_ms": elapsed_ms},
                    error=ErrorInfo(
                        error_code="TIME_BUDGET_EXCEEDED",
                        error_message="Engine 超出时间预算",
                        retryable=False,
                    ),
                )
                break

            self._append_event(
                state=state,
                event_type="state_update",
                step_id=f"step_{idx}",
                payload={"phase": "act_start", "step": step},
            )
            outcome = act_fn(state, step, idx)

            if outcome.status == "ok":
                stats.success_steps += 1
                self._append_event(
                    state=state,
                    event_type="state_update",
                    step_id=f"step_{idx}",
                    payload={"phase": "act_success", "step": step, "output": outcome.output},
                )
                continue

            stats.failed_steps += 1
            self._append_event(
                state=state,
                event_type="error",
                step_id=f"step_{idx}",
                payload={"step": step, "output": outcome.output},
                error=outcome.error
                or ErrorInfo(error_code="STEP_FAILED", error_message="步骤执行失败", retryable=False),
            )
            stats.stop_reason = "step_failed"
            break

        self._append_event(
            state=state,
            event_type="finish",
            step_id="step_finish",
            payload={
                "total_steps": stats.total_steps,
                "success_steps": stats.success_steps,
                "failed_steps": stats.failed_steps,
                "stop_reason": stats.stop_reason,
            },
        )
        state.final_answer = self._build_final_answer(stats)
        return state

    def _append_event(
        self,
        state: AgentState,
        event_type: Literal["plan", "tool_call", "tool_result", "state_update", "finish", "error"],
        step_id: str,
        payload: dict[str, Any],
        error: ErrorInfo | None = None,
    ) -> None:
        """统一写事件。

        集中写入可避免多处手写字段导致 trace 结构不一致。
        """

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

    def _build_final_answer(self, stats: _RunStats) -> FinalAnswer:
        """构造通用最终输出。"""

        status: Literal["success", "partial", "failed"] = "success"
        if stats.failed_steps > 0:
            status = "failed"
        elif stats.stop_reason != "finished":
            status = "partial"

        return FinalAnswer(
            status=status,
            summary=f"Engine 执行结束：{stats.stop_reason}",
            output={
                "total_steps": stats.total_steps,
                "success_steps": stats.success_steps,
                "failed_steps": stats.failed_steps,
                "stop_reason": stats.stop_reason,
            },
            artifacts=[{"type": "engine_stats", "name": "loop_result"}],
            references=[],
        )

