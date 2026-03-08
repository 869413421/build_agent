"""Engine pipeline 上下文与阶段定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal

from agent_forge.components.engine.domain.schemas import (
    ActFn,
    EngineLimits,
    ExecutionPlan,
    PlanFn,
    PlanStep,
    ReflectDecision,
    ReflectFn,
    RunContext,
    StepOutcome,
)
from agent_forge.components.protocol import AgentState, ErrorInfo


@dataclass(slots=True)
class RunStats:
    """运行统计聚合对象。

    Returns:
        RunStats: 当前 run 的累计统计信息。
    """

    total_planned_steps: int = 0
    executed_steps: int = 0
    success_steps: int = 0
    failed_steps: int = 0
    reflected_retry_count: int = 0
    skipped_steps: int = 0
    attempt_count: int = 0
    replan_count: int = 0
    stop_reason: str = "finished"


StageHandler = Callable[["EnginePipelineContext"], None | Awaitable[None]]
StageCustomizer = Callable[[list["EngineStage"]], list["EngineStage"]]


@dataclass(slots=True)
class EngineStage:
    """可插拔阶段定义。

    Args:
        name: 阶段名称。
        handler: 阶段处理函数。

    Returns:
        EngineStage: 单个可插拔阶段对象。
    """

    name: str
    handler: StageHandler


@dataclass(slots=True)
class EnginePipelineContext:
    """Engine pipeline 共享上下文。

    Args:
        state: 当前运行状态。
        run_context: 运行隔离与版本信息。
        plan_fn: 计划函数。
        act_fn: 执行函数。
        reflect_fn: 反思函数。
        started_at_ms: 启动时间戳。
        stats: 运行统计。
        event_writer: 统一事件写入函数。
        limits: Engine 限制配置。

    Returns:
        EnginePipelineContext: 供各阶段共享的上下文。
    """

    state: AgentState
    run_context: RunContext
    plan_fn: PlanFn
    act_fn: ActFn
    reflect_fn: ReflectFn
    started_at_ms: int
    stats: RunStats
    event_writer: Callable[
        [
            AgentState,
            Literal["plan", "tool_call", "tool_result", "state_update", "finish", "error"],
            str,
            dict[str, Any],
            ErrorInfo | None,
        ],
        None,
    ]
    limits: EngineLimits
    current_plan: ExecutionPlan | None = None
    plan_steps: list[PlanStep] = field(default_factory=list)
    completed_step_keys: set[str] = field(default_factory=set)
    current_step: PlanStep | None = None
    current_step_index: int = 0
    current_step_id: str = ""
    current_attempt: int = 0
    current_outcome: StepOutcome | None = None
    current_decision: ReflectDecision | None = None
    current_output_summary: str = ""
    current_output_hash: str = ""
    stop_requested: bool = False
    finish_emitted: bool = False
    retry_requested: bool = False
    replan_requested: bool = False
    step_completed: bool = False
    step_terminal: bool = False

    def append_event(
        self,
        event_type: Literal["plan", "tool_call", "tool_result", "state_update", "finish", "error"],
        step_id: str,
        payload: dict[str, Any],
        error: ErrorInfo | None = None,
    ) -> None:
        """通过统一入口写事件。

        Args:
            event_type: 事件类型。
            step_id: 步骤 ID。
            payload: 事件载荷。
            error: 错误对象。

        Returns:
            None
        """

        self.event_writer(self.state, event_type, step_id, payload, error)

    def request_stop(self, reason: str) -> None:
        """请求终止本轮运行。

        Args:
            reason: 停止原因。

        Returns:
            None
        """

        self.stats.stop_reason = reason
        self.stop_requested = True

    def prepare_step(self, step: PlanStep, step_index: int) -> None:
        """切换当前步骤。

        Args:
            step: 当前步骤。
            step_index: 步骤序号。

        Returns:
            None
        """

        self.current_step = step
        self.current_step_index = step_index
        self.current_step_id = f"step_{step_index}"

    def apply_plan(self, plan: ExecutionPlan) -> None:
        """将标准化计划写入上下文。

        Args:
            plan: 标准化执行计划。

        Returns:
            None
        """

        self.current_plan = plan
        self.plan_steps = list(plan.steps)
        self.stats.total_planned_steps = len(plan.steps)

    def replace_plan_steps(self, steps: list[PlanStep]) -> None:
        """同步替换当前运行计划中的全部步骤。
        Args:
            steps: 新的标准化步骤列表。
        Returns:
            None
        """

        normalized_steps = list(steps)
        if self.current_plan is None:
            self.current_plan = ExecutionPlan(steps=normalized_steps)
        else:
            self.current_plan = self.current_plan.model_copy(update={"steps": normalized_steps})
        self.plan_steps = normalized_steps
        self.stats.total_planned_steps = len(normalized_steps)

    def append_plan_steps(self, steps: list[PlanStep]) -> None:
        """向当前运行计划尾部追加步骤，并保持计划对象同步。
        Args:
            steps: 要追加的标准化步骤列表。
        Returns:
            None
        """

        if not steps:
            return
        self.replace_plan_steps([*self.plan_steps, *steps])

    def prepare_attempt(self, attempt: int) -> None:
        """重置当前尝试态。

        Args:
            attempt: 当前尝试序号。

        Returns:
            None
        """

        self.current_attempt = attempt
        self.current_outcome = None
        self.current_decision = None
        self.current_output_summary = ""
        self.current_output_hash = ""
        self.retry_requested = False
        self.replan_requested = False
        self.step_completed = False
        self.step_terminal = False

    def current_step_key(self) -> str:
        """返回当前步骤键。

        Returns:
            str: 当前步骤键；若无步骤则返回空字符串。
        """

        return self.current_step.key if self.current_step is not None else ""

    def current_step_name(self) -> str:
        """返回当前步骤名称。

        Returns:
            str: 当前步骤名称；若无步骤则返回空字符串。
        """

        return self.current_step.name if self.current_step is not None else ""
