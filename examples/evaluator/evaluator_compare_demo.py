"""Evaluator 对比示例。"""

from __future__ import annotations

from agent_forge.components.evaluator import EvaluationRequest, EvaluatorRuntime, RuleBasedEvaluator
from agent_forge.components.protocol import ExecutionEvent, FinalAnswer


def run_compare_demo() -> dict:
    runtime = EvaluatorRuntime(evaluators=[RuleBasedEvaluator()])
    good = runtime.evaluate(
        EvaluationRequest(
            trace_id="trace_good",
            run_id="run_good",
            task_input="整理投融资纪要",
            final_answer=FinalAnswer(status="success", summary="已整理完成。", output={"answer": "客户下周提交融资材料，并保持正式简洁风格。"}),
            events=[
                ExecutionEvent(trace_id="trace_good", run_id="run_good", step_id="plan_1", event_type="plan", payload={}),
                ExecutionEvent(trace_id="trace_good", run_id="run_good", step_id="finish_1", event_type="finish", payload={}),
            ],
            expected_answer="融资材料",
            reference_facts=["融资材料"],
            mode="combined",
        )
    )
    bad = runtime.evaluate(
        EvaluationRequest(
            trace_id="trace_bad",
            run_id="run_bad",
            task_input="整理投融资纪要",
            final_answer=FinalAnswer(status="success", summary="完成。", output={"answer": "一切正常"}),
            events=[
                ExecutionEvent(trace_id="trace_bad", run_id="run_bad", step_id="tool_1", event_type="tool_call", payload={}),
                ExecutionEvent(trace_id="trace_bad", run_id="run_bad", step_id="tool_1", event_type="tool_result", payload={"status": "error"}),
            ],
            expected_answer="融资材料",
            reference_facts=["融资材料"],
            mode="combined",
        )
    )
    return runtime.compare([good, bad])


if __name__ == "__main__":
    print(run_compare_demo())
