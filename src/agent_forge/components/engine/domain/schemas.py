"""Engine 领域类型定义。"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from agent_forge.components.protocol import AgentState, ErrorInfo, ExecutionEvent


class EngineLimits(BaseModel):
    """执行限制配置。

    Args:
        max_steps: 最大执行步数，只统计真实执行步骤。
        time_budget_ms: 整次 run 的总时间预算。
        step_timeout_ms: 单次步骤执行超时。
        max_retry_per_step: 单步最大重试次数。
        executor_max_workers: 共享执行池最大线程数。
        max_inflight_acts: 同时在途 act 数量上限。
        trace_output_preview_chars: trace 输出预览最大字符数。

    Returns:
        EngineLimits: 校验后的执行限制对象。
    """

    max_steps: int = Field(default=8, ge=1, description="最大执行步数（只统计实际执行步）")
    time_budget_ms: int = Field(default=3000, ge=1, description="run 级时间预算（毫秒）")
    step_timeout_ms: int = Field(default=1200, ge=1, description="单步超时（毫秒）")
    max_retry_per_step: int = Field(default=1, ge=0, description="单步最大重试次数")
    max_replans: int = Field(default=2, ge=0, description="单次 run 允许的最大重规划次数")
    executor_max_workers: int = Field(default=8, ge=1, description="共享执行池线程数")
    max_inflight_acts: int = Field(default=32, ge=1, description="同时在途 act 上限（背压）")
    trace_output_preview_chars: int = Field(default=240, ge=32, description="trace 输出预览最大字符数")


class StepOutcome(BaseModel):
    """单步执行结果。

    Args:
        status: 步骤状态。
        output: 步骤输出。
        error: 错误信息。

    Returns:
        StepOutcome: 标准化后的步骤结果。
    """

    status: Literal["ok", "error"] = Field(..., description="步骤状态")
    output: dict[str, Any] = Field(default_factory=dict, description="步骤输出")
    error: ErrorInfo | None = Field(default=None, description="错误信息")


class ReflectDecision(BaseModel):
    """反思决策结果。

    Args:
        action: 反思动作。
        reason: 决策原因。
        replacement_plan: 当动作是 replan 时提供的新计划。
        plan_update_mode: 重规划时如何处理剩余步骤。

    Returns:
        ReflectDecision: 标准化决策对象。
    """

    action: Literal["continue", "retry", "abort", "replan"] = Field(..., description="反思动作")
    reason: str = Field(default="", description="决策原因")
    replacement_plan: ExecutionPlan | None = Field(default=None, description="重规划后的替换计划")
    plan_update_mode: Literal["replace_remaining", "append_remaining"] = Field(
        default="replace_remaining", description="重规划更新模式"
    )


class RunContext(BaseModel):
    """运行隔离与版本上下文。

    Args:
        tenant_id: 租户 ID。
        user_id: 用户 ID。
        config_version: 配置版本。
        model_version: 模型版本。
        tool_version: 工具版本。
        policy_version: 策略版本。

    Returns:
        RunContext: 校验后的运行上下文。
    """

    tenant_id: str | None = Field(default=None, description="租户 ID（可选）")
    user_id: str | None = Field(default=None, description="用户 ID（可选）")
    config_version: str = Field(default="v1", description="配置版本")
    model_version: str = Field(default="unset", description="模型版本")
    tool_version: str = Field(default="unset", description="工具版本")
    policy_version: str = Field(default="v1", description="策略版本")


class PlanStep(BaseModel):
    """标准化步骤对象。

    Args:
        key: 稳定步骤键。
        name: 步骤名称。
        kind: 步骤类型，用于区分检索、工具、生成等执行意图。
        payload: 步骤扩展数据。
        depends_on: 依赖步骤键列表。
        priority: 执行优先级，数值越小优先级越高。
        timeout_ms: 当前步骤的超时覆盖值。
        max_retry_per_step: 当前步骤的重试覆盖值。
        metadata: 步骤元数据。

    Returns:
        PlanStep: 标准化后的步骤对象。
    """

    key: str = Field(..., min_length=1, description="稳定步骤键")
    name: str = Field(..., min_length=1, description="步骤名称")
    kind: str = Field(default="generic", min_length=1, description="步骤类型")
    payload: dict[str, Any] = Field(default_factory=dict, description="步骤扩展数据")
    depends_on: list[str] = Field(default_factory=list, description="依赖步骤键")
    priority: int = Field(default=100, description="步骤优先级")
    timeout_ms: int | None = Field(default=None, ge=1, description="步骤级超时覆盖")
    max_retry_per_step: int | None = Field(default=None, ge=0, description="步骤级重试覆盖")
    metadata: dict[str, Any] = Field(default_factory=dict, description="步骤元数据")


class PlanAudit(BaseModel):
    """计划审计信息。
    Args:
        created_by: 计划创建来源，例如 planner、human、policy。
        previous_revision: 上一个计划修订号。
        triggered_by_step_key: 触发重规划的步骤键。
        triggered_by_step_name: 触发重规划的步骤名称。
        change_summary: 本次计划生成或修订摘要。
    Returns:
        PlanAudit: 标准化后的计划审计对象。
    """

    created_by: str = Field(default="planner", description="计划创建来源")
    previous_revision: int | None = Field(default=None, ge=1, description="上一个计划修订号")
    triggered_by_step_key: str = Field(default="", description="触发计划变化的步骤键")
    triggered_by_step_name: str = Field(default="", description="触发计划变化的步骤名称")
    change_summary: str = Field(default="", description="本次计划变化摘要")


class ExecutionPlan(BaseModel):
    """标准化执行计划对象。

    Args:
        plan_id: 计划唯一 ID。
        revision: 计划修订号。
        origin: 计划来源，例如 initial、replan、human_patch。
        reason: 本次计划生成或修订原因。
        global_task: 本轮计划服务的全局任务。
        steps: 标准化步骤列表。
        metadata: 计划元数据。

    Returns:
        ExecutionPlan: 标准化执行计划。
    """

    plan_id: str = Field(default_factory=lambda: f"plan_{uuid4().hex}", min_length=1, description="计划 ID")
    revision: int = Field(default=1, ge=1, description="计划修订号")
    origin: str = Field(default="initial", min_length=1, description="计划来源")
    reason: str = Field(default="", description="计划生成原因")
    global_task: str = Field(default="", description="全局任务目标")
    success_criteria: list[str] = Field(default_factory=list, description="计划成功判定标准")
    constraints: list[str] = Field(default_factory=list, description="计划执行约束")
    risk_level: Literal["low", "medium", "high", "critical"] = Field(default="medium", description="计划风险等级")
    audit: PlanAudit = Field(default_factory=PlanAudit, description="计划审计信息")
    steps: list[PlanStep] = Field(default_factory=list, description="标准化步骤列表")
    metadata: dict[str, Any] = Field(default_factory=dict, description="计划元数据")


PlanInput = list[str | dict[str, Any] | PlanStep] | ExecutionPlan
PlanFn = Callable[[AgentState], PlanInput]
ActFn = Callable[[AgentState, PlanStep, int], StepOutcome | Awaitable[StepOutcome]]
ReflectFn = Callable[
    [AgentState, PlanStep, int, StepOutcome], ReflectDecision | Awaitable[ReflectDecision]
]
ActExecutor = Callable[[ActFn, AgentState, PlanStep, int, int], Awaitable[StepOutcome]]
EngineEventListener = Callable[[ExecutionEvent], None]
