"""Chapter 06: Observability end-to-end runnable demo."""

from __future__ import annotations

import asyncio

from agent_forge.components.engine import EngineLimits, EngineLoop, PlanStep, StepOutcome
from agent_forge.components.observability import ObservabilityRuntime, SamplingPolicy
from agent_forge.components.protocol import AgentState, ToolCall, build_initial_state
from agent_forge.components.tool_runtime import PythonMathTool, ToolRuntime, ToolSpec, build_python_math_handler


def create_observability_runtime() -> ObservabilityRuntime:
    """Create runtime with full sampling for demonstration output."""

    return ObservabilityRuntime(sampling_policy=SamplingPolicy(success_sample_rate=1.0))


def create_tool_runtime(observability: ObservabilityRuntime) -> ToolRuntime:
    """Create ToolRuntime and register observability hook + python_math tool."""

    runtime = ToolRuntime()
    runtime.register_hook(observability.build_tool_hook())
    runtime.register_tool(
        ToolSpec(
            name="python_math",
            args_schema={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        ),
        build_python_math_handler(PythonMathTool()),
    )
    return runtime


def run_tool_runtime_path(observability: ObservabilityRuntime, runtime: ToolRuntime) -> tuple[str, str]:
    """Run one success + one failure tool call and return (trace_id, run_id)."""

    trace_id = "trace_obs_demo_tool"
    run_id = "run_obs_demo_tool"
    observability.set_default_context(trace_id=trace_id, run_id=run_id)

    success = runtime.execute(
        ToolCall(
            tool_call_id="tc_math_ok",
            tool_name="python_math",
            principal="demo_user",
            args={"expression": "(2 + 3) * 7"},
        )
    )
    failure = runtime.execute(
        ToolCall(
            tool_call_id="tc_math_missing",
            tool_name="missing_tool",
            principal="demo_user",
            args={},
        )
    )

    print("[tool_runtime] success:", success.status, success.output)
    print("[tool_runtime] failure:", failure.status, failure.error.error_code if failure.error else None)
    return trace_id, run_id


async def run_engine_path(observability: ObservabilityRuntime, runtime: ToolRuntime) -> tuple[str, str]:
    """Run Engine once with event_listener callback and return (trace_id, run_id)."""

    state = build_initial_state("session_obs_demo_engine")
    observability.set_default_context(trace_id=state.trace_id, run_id=state.run_id)

    engine = EngineLoop(
        limits=EngineLimits(max_steps=2, time_budget_ms=5000),
        event_listener=observability.engine_event_listener,
    )

    def plan_fn(_: AgentState) -> list[dict]:
        return [{"id": "step_math", "name": "tool_math", "payload": {"expression": "sqrt(16) + 1"}}]

    async def act_fn(_: AgentState, step: PlanStep, __: int) -> StepOutcome:
        call = ToolCall(
            tool_call_id=f"tc_{step.key}",
            tool_name="python_math",
            principal="demo_user",
            args={"expression": str(step.payload.get("expression", "1+1"))},
        )
        result = await runtime.execute_async(call)
        if result.status == "ok":
            return StepOutcome(status="ok", output=result.output)
        return StepOutcome(status="error", output=result.output, error=result.error)

    updated = await engine.arun(state, plan_fn=plan_fn, act_fn=act_fn)
    print("[engine] final status:", updated.final_answer.status if updated.final_answer else "none")
    return state.trace_id, state.run_id


def print_observability_summary(observability: ObservabilityRuntime, trace_id: str, run_id: str, title: str) -> None:
    """Print replay + metrics summary for one trace/run pair."""

    replay = observability.replay_structure(trace_id=trace_id, run_id=run_id)
    metrics = observability.aggregate_metrics(trace_id=trace_id, run_id=run_id)
    export = observability.export(trace_id=trace_id, run_id=run_id)
    print(f"[{title}] traces={len(export.traces)} tool_records={len(replay.tool_records)} metrics={metrics}")


def main() -> None:
    """Run chapter demo."""

    # 1. Build runtimes and register hook/tool.
    observability = create_observability_runtime()
    runtime = create_tool_runtime(observability)

    # 2. Run tool path: one success + one failure.
    tool_trace_id, tool_run_id = run_tool_runtime_path(observability, runtime)

    # 3. Run engine path with callback injection.
    engine_trace_id, engine_run_id = asyncio.run(run_engine_path(observability, runtime))

    # 4. Print observability summaries for both paths.
    print_observability_summary(observability, tool_trace_id, tool_run_id, "tool_path")
    print_observability_summary(observability, engine_trace_id, engine_run_id, "engine_path")


if __name__ == "__main__":
    main()

