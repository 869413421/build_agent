"""Evaluator judge 测试。"""

from __future__ import annotations

from typing import Any

from agent_forge.components.evaluator import EvaluationRequest, EvaluationRubric, ModelRuntimeJudgeEvaluator
from agent_forge.components.model_runtime import ModelRequest, ModelResponse, ModelStats
from agent_forge.components.protocol import FinalAnswer


class _FakeJudgeRuntime:
    def __init__(self, parsed_output: dict[str, Any]) -> None:
        self.parsed_output = parsed_output
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        self.requests.append(request)
        _ = kwargs
        return ModelResponse(content="{}", parsed_output=self.parsed_output, stats=ModelStats(total_tokens=18))


def test_evaluator_judge_should_use_model_runtime_and_parse_scores() -> None:
    fake = _FakeJudgeRuntime({"verdict": "pass", "total_score": 0.9, "summary": "结果较好", "scores": [{"dimension": "correctness", "score": 0.9, "reason": "命中目标"}]})
    evaluator = ModelRuntimeJudgeEvaluator(model_runtime=fake)
    result = evaluator.evaluate(
        EvaluationRequest(
            task_input="整理纪要",
            final_answer=FinalAnswer(status="success", summary="完成", output={"answer": "融资材料"}),
            expected_answer="融资材料",
            rubric=EvaluationRubric(name="judge_rubric", dimensions=["correctness"], weights={"correctness": 2.0}),
            mode="output",
        )
    )
    assert fake.requests[0].response_schema is not None
    assert "\"correctness\"" in fake.requests[0].system_prompt
    assert "{\"answer\": \"融资材料\"}" in fake.requests[0].messages[0].content
    assert result.verdict == "pass"
    assert result.total_score == 0.9
    assert result.scores[0].dimension == "correctness"


def test_evaluator_judge_should_degrade_when_output_is_invalid() -> None:
    fake = _FakeJudgeRuntime({"summary": "缺字段"})
    evaluator = ModelRuntimeJudgeEvaluator(model_runtime=fake)
    result = evaluator.evaluate(EvaluationRequest(mode="combined"))
    assert result.verdict == "warning"
    assert result.total_score == 0.0
    assert "judge" in result.summary
