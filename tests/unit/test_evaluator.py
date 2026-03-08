"""Evaluator 主流程测试。"""

from __future__ import annotations

from agent_forge.components.evaluator import EvaluationRequest, EvaluationRubric, EvaluatorRuntime, RuleBasedEvaluator, summarize_events
from agent_forge.components.protocol import ExecutionEvent, FinalAnswer


def test_evaluator_should_score_output_and_trajectory() -> None:
    runtime = EvaluatorRuntime(evaluators=[RuleBasedEvaluator()])
    result = runtime.evaluate(
        EvaluationRequest(
            trace_id="trace_eval",
            run_id="run_eval",
            task_input="整理纪要",
            final_answer=FinalAnswer(status="success", summary="已整理完成。", output={"answer": "客户下周提交融资材料，并保持结论前置。"}),
            events=[
                ExecutionEvent(trace_id="trace_eval", run_id="run_eval", step_id="plan_1", event_type="plan", payload={}),
                ExecutionEvent(trace_id="trace_eval", run_id="run_eval", step_id="finish_1", event_type="finish", payload={}),
            ],
            expected_answer="融资材料",
            reference_facts=["融资材料", "结论前置"],
            mode="combined",
        )
    )
    assert result.verdict in {"pass", "warning"}
    assert result.total_score > 0.5
    assert any(item.dimension == "correctness" for item in result.scores)
    assert any(item.dimension == "efficiency" for item in result.scores)


def test_evaluator_should_warn_when_tool_failed_but_answer_looks_successful() -> None:
    runtime = EvaluatorRuntime(evaluators=[RuleBasedEvaluator()])
    result = runtime.evaluate(
        EvaluationRequest(
            final_answer=FinalAnswer(status="success", summary="已完成。", output={"answer": "一切正常"}),
            events=[
                ExecutionEvent(trace_id="trace_a", run_id="run_a", step_id="tool_1", event_type="tool_call", payload={}),
                ExecutionEvent(trace_id="trace_a", run_id="run_a", step_id="tool_1", event_type="tool_result", payload={"status": "error"}),
            ],
            mode="trajectory",
        )
    )
    tool_score = next(item for item in result.scores if item.dimension == "tool_effectiveness")
    assert tool_score.score <= 0.5


def test_evaluator_should_fail_when_answer_is_empty() -> None:
    runtime = EvaluatorRuntime(evaluators=[RuleBasedEvaluator()])
    result = runtime.evaluate(EvaluationRequest(final_answer=None, mode="output"))
    assert result.verdict == "fail"


def test_evaluator_should_compare_two_results() -> None:
    runtime = EvaluatorRuntime(evaluators=[RuleBasedEvaluator()])
    first = runtime.evaluate(EvaluationRequest(trace_id="trace_1", run_id="run_1", final_answer=FinalAnswer(status="success", summary="完成", output={"answer": "融资材料"}), expected_answer="融资材料", mode="output"))
    second = runtime.evaluate(EvaluationRequest(trace_id="trace_2", run_id="run_2", final_answer=FinalAnswer(status="success", summary="完成", output={"answer": "未知"}), expected_answer="融资材料", mode="output"))
    compare = runtime.compare([first, second])
    assert compare["winner"]["run_id"] == "run_1"
    assert compare["winner"]["evaluator"] == first.evaluator_name
    assert len(compare["ranking"]) == 2


def test_evaluator_should_summarize_events() -> None:
    summary = summarize_events([
        ExecutionEvent(trace_id="trace_s", run_id="run_s", step_id="plan_1", event_type="plan", payload={}),
        ExecutionEvent(trace_id="trace_s", run_id="run_s", step_id="tool_1", event_type="tool_call", payload={}),
        ExecutionEvent(trace_id="trace_s", run_id="run_s", step_id="tool_1", event_type="tool_result", payload={"status": "error"}),
    ])
    assert summary.total_events == 3
    assert summary.total_tool_calls == 1
    assert summary.total_tool_errors == 1


def test_evaluator_should_count_same_replan_revision_only_once() -> None:
    summary = summarize_events([
        ExecutionEvent(trace_id="trace_r", run_id="run_r", step_id="plan_1", event_type="plan", payload={"plan_revision": 2, "plan_origin": "replan"}),
        ExecutionEvent(trace_id="trace_r", run_id="run_r", step_id="finish_1", event_type="finish", payload={"plan_revision": 2, "plan_origin": "replan"}),
    ])
    assert summary.total_replans == 1


def test_evaluator_should_apply_rubric_dimensions_and_weights() -> None:
    runtime = EvaluatorRuntime(evaluators=[RuleBasedEvaluator()])
    rubric = EvaluationRubric(
        name="focused_rubric",
        dimensions=["correctness", "groundedness"],
        weights={"correctness": 3.0, "groundedness": 1.0},
    )
    result = runtime.evaluate(
        EvaluationRequest(
            final_answer=FinalAnswer(status="success", summary="完成", output={"answer": "融资材料"}),
            expected_answer="融资材料",
            reference_facts=["缺失事实"],
            rubric=rubric,
            mode="output",
        )
    )
    assert {item.dimension for item in result.scores} == {"correctness", "groundedness"}
    assert result.total_score == 0.75


def test_evaluator_should_build_candidate_id_when_run_identity_is_missing() -> None:
    runtime = EvaluatorRuntime(evaluators=[RuleBasedEvaluator()])
    first = runtime.evaluate(EvaluationRequest(final_answer=FinalAnswer(status="success", summary="完成", output={"answer": "融资材料"}), expected_answer="融资材料", mode="output"))
    second = runtime.evaluate(EvaluationRequest(final_answer=FinalAnswer(status="success", summary="完成", output={"answer": "未知"}), expected_answer="融资材料", mode="output"))
    compare = runtime.compare([first, second])
    assert compare["winner"]["candidate_id"].startswith("rule_based_evaluator:output:")
