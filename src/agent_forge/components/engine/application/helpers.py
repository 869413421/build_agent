"""Engine 运行辅助函数。"""

from __future__ import annotations

import hashlib
import json
from time import monotonic
from typing import Any, Literal

from agent_forge.components.engine.application.context import RunStats
from agent_forge.components.engine.domain.schemas import EngineLimits, ExecutionPlan, PlanAudit, PlanInput, PlanStep
from agent_forge.components.protocol import AgentState, FinalAnswer


def default_now_ms() -> int:
    """返回当前毫秒时间戳。

    Returns:
        int: 当前单调时钟毫秒值。
    """

    return int(monotonic() * 1000)


def build_final_answer(stats: RunStats, started_at: int, now_ms: int) -> FinalAnswer:
    """构造通用最终输出。

    Args:
        stats: 运行统计。
        started_at: 启动时间戳。
        now_ms: 当前时间戳。

    Returns:
        FinalAnswer: 面向上层稳定暴露的最终结果。
    """

    status: Literal["success", "partial", "failed"] = "success"
    if stats.failed_steps > 0:
        status = "failed"
    elif stats.stop_reason != "finished":
        status = "partial"

    elapsed_ms = max(1, now_ms - started_at)
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
            "replan_count": stats.replan_count,
            "skipped_steps": stats.skipped_steps,
            "attempt_count": stats.attempt_count,
            "stop_reason": stats.stop_reason,
            "elapsed_ms": elapsed_ms,
            "steps_per_second": steps_per_second,
        },
        artifacts=[{"type": "engine_stats", "name": "loop_result"}],
        references=[],
    )


def completed_step_keys(state: AgentState) -> set[str]:
    """提取历史已完成步骤键。

    Args:
        state: 运行状态。

    Returns:
        set[str]: 已完成步骤键集合。
    """

    for event in reversed(state.events):
        if event.event_type != "finish":
            continue
        keys = event.payload.get("completed_step_keys")
        if isinstance(keys, list):
            parsed = {item for item in keys if isinstance(item, str) and item}
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


def exceed_time_budget(started_at: int, time_budget_ms: int, now_ms: int) -> bool:
    """检查 run 级时间预算。

    Args:
        started_at: 启动时间。
        time_budget_ms: 总预算毫秒。
        now_ms: 当前时间。

    Returns:
        bool: 是否已超预算。
    """

    return (now_ms - started_at) > time_budget_ms


def summarize_output(output: dict[str, Any], limits: EngineLimits) -> tuple[str, str]:
    """对步骤输出做摘要。

    Args:
        output: 步骤输出。
        limits: Engine 限制配置。

    Returns:
        tuple[str, str]: 输出摘要与输出哈希。
    """

    raw = json.dumps(output, ensure_ascii=False, sort_keys=True)
    output_hash = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    preview = raw[: limits.trace_output_preview_chars]
    summary = f"len={len(raw)},preview={preview}"
    return summary, output_hash


def normalize_execution_plan(raw_plan: PlanInput) -> ExecutionPlan:
    """标准化执行计划。

    Args:
        raw_plan: 原始计划输入。

    Returns:
        ExecutionPlan: 标准化后的执行计划对象。
    """

    normalized: list[PlanStep] = []
    if isinstance(raw_plan, ExecutionPlan):
        if not raw_plan.steps:
            return raw_plan.model_copy(update={"steps": []})
        for step in raw_plan.steps:
            normalized.append(_normalize_step(step))
        return raw_plan.model_copy(update={"steps": normalized})

    for item in raw_plan:
        if isinstance(item, PlanStep):
            normalized.append(_normalize_step(item))
            continue
        if isinstance(item, str):
            key = stable_hash({"name": item})
            normalized.append(PlanStep(key=key, name=item, payload={}))
            continue
        step_id = item.get("id") if isinstance(item.get("id"), str) else ""
        step_name = item.get("name") if isinstance(item.get("name"), str) else "unnamed_step"
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        if not step_id:
            step_id = stable_hash({"name": step_name, "payload": payload})
        normalized.append(
            PlanStep(
                key=step_id,
                name=step_name,
                kind=item.get("kind") if isinstance(item.get("kind"), str) and item.get("kind") else "generic",
                payload=payload,
                depends_on=item.get("depends_on") if isinstance(item.get("depends_on"), list) else [],
                priority=item.get("priority") if isinstance(item.get("priority"), int) else 100,
                timeout_ms=item.get("timeout_ms") if isinstance(item.get("timeout_ms"), int) else None,
                max_retry_per_step=item.get("max_retry_per_step")
                if isinstance(item.get("max_retry_per_step"), int)
                else None,
                metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
            )
        )

    return ExecutionPlan(steps=normalized)


def build_replanned_plan(
    current_plan: ExecutionPlan | None,
    replacement_plan: ExecutionPlan,
    reason: str,
    trigger_step: PlanStep | None = None,
) -> ExecutionPlan:
    """构建重规划后的标准计划。

    Args:
        current_plan: 当前运行中的计划。
        replacement_plan: reflect 返回的新计划。
        reason: 本次重规划原因。

    Returns:
        ExecutionPlan: 修订后的计划对象。
    """

    replacement_fields = set(replacement_plan.model_fields_set)
    replacement_audit_fields = set(replacement_plan.audit.model_fields_set) if "audit" in replacement_fields else set()
    normalized = normalize_execution_plan(replacement_plan)
    base_plan = current_plan or ExecutionPlan()
    next_revision = normalized.revision if normalized.revision > base_plan.revision else base_plan.revision + 1
    next_risk_level = normalized.risk_level if "risk_level" in replacement_fields else base_plan.risk_level
    next_created_by = normalized.audit.created_by if "created_by" in replacement_audit_fields else base_plan.audit.created_by
    next_change_summary = (
        normalized.audit.change_summary
        if "change_summary" in replacement_audit_fields
        else normalized.reason or reason
    )
    return normalized.model_copy(
        update={
            "plan_id": base_plan.plan_id,
            "revision": next_revision,
            "origin": normalized.origin if normalized.origin != "initial" else "replan",
            "reason": normalized.reason or reason,
            "global_task": normalized.global_task or base_plan.global_task,
            "success_criteria": normalized.success_criteria or list(base_plan.success_criteria),
            "constraints": normalized.constraints or list(base_plan.constraints),
            "risk_level": next_risk_level,
            "audit": PlanAudit(
                created_by=next_created_by,
                previous_revision=base_plan.revision,
                triggered_by_step_key=trigger_step.key if trigger_step is not None else "",
                triggered_by_step_name=trigger_step.name if trigger_step is not None else "",
                change_summary=next_change_summary,
            ),
            "metadata": {**base_plan.metadata, **normalized.metadata},
        }
    )


def schedule_execution_plan(plan: ExecutionPlan, completed_keys: set[str] | None = None) -> ExecutionPlan:
    """按依赖与优先级收口执行顺序。
    Args:
        plan: 原始标准化计划对象。
        completed_keys: 已完成步骤键集合，用于满足外部依赖。
    Returns:
        ExecutionPlan: 调度后的计划对象。
    Raises:
        ValueError: 依赖缺失或存在循环依赖时抛出。
    """

    completed = completed_keys or set()
    steps = list(plan.steps)
    if not steps:
        return plan.model_copy(update={"steps": []})

    step_by_key = {step.key: step for step in steps}
    missing_dependencies: list[str] = []
    for step in steps:
        for dependency in step.depends_on:
            if dependency in completed:
                continue
            if dependency not in step_by_key:
                missing_dependencies.append(f"{step.key}->{dependency}")
    if missing_dependencies:
        missing = ", ".join(sorted(missing_dependencies))
        raise ValueError(f"plan contains missing dependencies: {missing}")

    original_order = {step.key: index for index, step in enumerate(steps)}
    satisfied = set(completed)
    remaining = {step.key: step for step in steps}
    scheduled: list[PlanStep] = []

    while remaining:
        ready = [
            step
            for step in remaining.values()
            if all(dependency in satisfied for dependency in step.depends_on)
        ]
        if not ready:
            cycle_nodes = ", ".join(sorted(remaining.keys()))
            raise ValueError(f"plan contains cyclic dependencies: {cycle_nodes}")

        ready.sort(key=lambda step: (step.priority, original_order[step.key]))
        selected = ready[0]
        scheduled.append(selected)
        satisfied.add(selected.key)
        remaining.pop(selected.key)

    return plan.model_copy(update={"steps": scheduled})


def normalize_plan_steps(raw_plan: PlanInput) -> list[PlanStep]:
    """向后兼容的步骤标准化入口。

    Args:
        raw_plan: 原始计划输入。

    Returns:
        list[PlanStep]: 标准化后的步骤列表。
    """

    return normalize_execution_plan(raw_plan).steps


def _normalize_step(step: PlanStep) -> PlanStep:
    """收口单个步骤对象。

    Args:
        step: 原始步骤对象。

    Returns:
        PlanStep: 规范化后的步骤对象。
    """

    return step.model_copy(
        update={
            "kind": step.kind or "generic",
            "depends_on": list(step.depends_on),
            "payload": dict(step.payload),
            "metadata": dict(step.metadata),
        }
    )


def stable_hash(value: dict[str, Any]) -> str:
    """生成稳定哈希。

    Args:
        value: 待哈希对象。

    Returns:
        str: 稳定步骤键。
    """

    raw = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return f"step_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"
