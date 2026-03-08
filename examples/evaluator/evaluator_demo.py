"""Evaluator 示例。"""

from __future__ import annotations

from typing import Any

from agent_forge.components.evaluator import EvaluationRequest, EvaluatorRuntime, ModelRuntimeJudgeEvaluator, RuleBasedEvaluator
from agent_forge.components.model_runtime import ModelRequest, ModelResponse, ModelStats
from agent_forge.components.protocol import ExecutionEvent, FinalAnswer, build_initial_state


class DemoJudgeRuntime:
    """示例用假 judge runtime。"""

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        _ = kwargs
        _ = request
        return ModelResponse(
            content='{"verdict":"pass"}',
            parsed_output={
                "verdict": "pass",
                "total_score": 0.86,
                "summary": "输出基本满足目标，轨迹也较稳定。",
                "strengths": ["回答完整", "轨迹清晰"],
                "weaknesses": ["仍可补充更多引用事实"],
                "suggestions": ["补充 reference_facts 可进一步提高 groundedness"],
                "scores": [
                    {"dimension": "correctness", "score": 0.9, "reason": "命中目标"},
                    {"dimension": "efficiency", "score": 0.82, "reason": "步骤数可接受"},
                ],
            },
            stats=ModelStats(total_tokens=24),
        )


def run_demo() -> dict[str, Any]:
    state = build_initial_state("session_eval_demo")
    state.final_answer = FinalAnswer(
        status="success",
        summary="已整理出董事会纪要的关键结论。",
        output={"answer": "董事会要求下周提交融资材料，并保持结论前置。"},
    )
    state.events = [
        ExecutionEvent(trace_id=state.trace_id, run_id=state.run_id, step_id="plan_1", event_type="plan", payload={}),
        ExecutionEvent(trace_id=state.trace_id, run_id=state.run_id, step_id="tool_1", event_type="tool_call", payload={}),
        ExecutionEvent(trace_id=state.trace_id, run_id=state.run_id, step_id="tool_1", event_type="tool_result", payload={"status": "ok"}),
        ExecutionEvent(trace_id=state.trace_id, run_id=state.run_id, step_id="finish_1", event_type="finish", payload={}),
    ]
    runtime = EvaluatorRuntime(evaluators=[RuleBasedEvaluator(), ModelRuntimeJudgeEvaluator(model_runtime=DemoJudgeRuntime())])
    result = runtime.evaluate(
        EvaluationRequest(
            trace_id=state.trace_id,
            run_id=state.run_id,
            task_input="请整理董事会纪要",
            agent_state=state,
            final_answer=state.final_answer,
            events=state.events,
            expected_answer="融资材料",
            reference_facts=["融资材料", "结论前置"],
            mode="combined",
        )
    )
    return {
        "verdict": result.verdict,
        "total_score": result.total_score,
        "score_count": len(result.scores),
        "summary": result.summary,
    }


if __name__ == "__main__":
    print(run_demo())
