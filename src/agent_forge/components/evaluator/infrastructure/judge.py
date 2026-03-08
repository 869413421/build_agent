"""LLM judge 评估器。"""

from __future__ import annotations

import json
from typing import Any

from agent_forge.components.evaluator.application.runtime import summarize_events
from agent_forge.components.evaluator.domain import EvaluationRequest, EvaluationResult, EvaluationScore, EvaluatorModelRuntime
from agent_forge.components.model_runtime import ModelRequest
from agent_forge.components.protocol import AgentMessage


class ModelRuntimeJudgeEvaluator:
    """通过 ModelRuntime 做结构化评估。"""

    evaluator_name = "model_runtime_judge"
    evaluator_version = "judge-v1"

    def __init__(self, *, model_runtime: EvaluatorModelRuntime, model: str | None = None) -> None:
        self._model_runtime = model_runtime
        self._model = model

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        model_request = ModelRequest(
            messages=[AgentMessage(role="user", content=_build_user_prompt(request))],
            system_prompt=_build_system_prompt(request),
            model=self._model,
            temperature=0.0,
            response_schema=_judge_schema(),
        )
        try:
            response = self._model_runtime.generate(model_request)
            parsed = response.parsed_output or {}
            return _parse_judge_result(parsed=parsed, request=request)
        except Exception as exc:
            return EvaluationResult(
                verdict="warning",
                total_score=0.0,
                scores=[],
                summary=f"judge 评估失败：{exc}",
                strengths=[],
                weaknesses=["judge 未能返回结构化结果"],
                suggestions=["检查 ModelRuntime judge schema 或模型输出稳定性"],
                evaluator_name=self.evaluator_name,
                evaluator_version=self.evaluator_version,
                mode=request.mode,
                trace_id=request.trace_id,
                run_id=request.run_id,
                metadata={"error": str(exc)},
            )


def _build_system_prompt(request: EvaluationRequest) -> str:
    rubric_text = request.rubric.instructions if request.rubric else "按 correctness、groundedness、efficiency 等维度结构化打分。"
    dimensions = request.rubric.dimensions if request.rubric and request.rubric.dimensions else ["correctness", "groundedness", "completeness", "instruction_following", "tool_effectiveness", "efficiency", "memory_usefulness"]
    weights = request.rubric.weights if request.rubric else {}
    return (
        f"你是 Agent 结果评估器。请基于输入材料输出结构化 JSON。不要输出自由文本。当前模式是 {request.mode}。"
        f"启用维度：{json.dumps(dimensions, ensure_ascii=False)}。"
        f"维度权重：{json.dumps(weights, ensure_ascii=False)}。"
        f"补充要求：{rubric_text}"
    )


def _build_user_prompt(request: EvaluationRequest) -> str:
    final_answer = request.final_answer or (request.agent_state.final_answer if request.agent_state else None)
    trajectory = summarize_events(request.events or (request.agent_state.events if request.agent_state else []))
    return (
        f"task_input:\n{request.task_input}\n\n"
        f"final_answer_summary:\n{final_answer.summary if final_answer else ''}\n\n"
        f"final_answer_output:\n{json.dumps(final_answer.output if final_answer else {}, ensure_ascii=False, sort_keys=True)}\n\n"
        f"expected_answer:\n{request.expected_answer or ''}\n\n"
        f"reference_facts:\n{json.dumps(request.reference_facts, ensure_ascii=False)}\n\n"
        f"trajectory_summary:\n{json.dumps(trajectory.model_dump(), ensure_ascii=False, sort_keys=True)}\n"
    )


def _judge_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["verdict", "total_score", "summary", "scores"],
        "properties": {
            "verdict": {"type": "string", "enum": ["pass", "warning", "fail"]},
            "total_score": {"type": "number"},
            "summary": {"type": "string"},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "weaknesses": {"type": "array", "items": {"type": "string"}},
            "suggestions": {"type": "array", "items": {"type": "string"}},
            "scores": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["dimension", "score", "reason"],
                    "properties": {
                        "dimension": {
                            "type": "string",
                            "enum": [
                                "correctness",
                                "groundedness",
                                "completeness",
                                "instruction_following",
                                "tool_effectiveness",
                                "efficiency",
                                "memory_usefulness",
                            ],
                        },
                        "score": {"type": "number"},
                        "reason": {"type": "string"},
                        "evidence": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
    }


def _parse_judge_result(*, parsed: dict[str, Any], request: EvaluationRequest) -> EvaluationResult:
    raw_scores = parsed.get("scores", [])
    scores: list[EvaluationScore] = []
    for item in raw_scores:
        if not isinstance(item, dict):
            continue
        try:
            scores.append(EvaluationScore.model_validate(item))
        except Exception:
            continue
    if "verdict" not in parsed or "total_score" not in parsed:
        return EvaluationResult(
            verdict="warning",
            total_score=0.0,
            scores=[],
            summary="judge 输出缺少关键字段，已退化为空结果",
            strengths=[],
            weaknesses=["judge 输出不完整"],
            suggestions=["检查 judge schema 与模型输出"],
            evaluator_name="model_runtime_judge",
            evaluator_version="judge-v1",
            mode=request.mode,
            trace_id=request.trace_id,
            run_id=request.run_id,
            metadata={"raw_output": parsed},
        )
    return EvaluationResult(
        verdict=parsed["verdict"],
        total_score=float(parsed["total_score"]),
        scores=scores,
        summary=str(parsed.get("summary", "")),
        strengths=list(parsed.get("strengths", [])),
        weaknesses=list(parsed.get("weaknesses", [])),
        suggestions=list(parsed.get("suggestions", [])),
        evaluator_name="model_runtime_judge",
        evaluator_version="judge-v1",
        mode=request.mode,
        trace_id=request.trace_id,
        run_id=request.run_id,
        metadata={"raw_output": parsed},
    )
