"""规则评估器。"""

from __future__ import annotations

import json
from typing import Any

from agent_forge.components.evaluator.application.runtime import _calculate_total_score, summarize_events
from agent_forge.components.evaluator.domain import EvaluationRequest, EvaluationResult, EvaluationScore, EvaluationVerdict


class RuleBasedEvaluator:
    """基于显式规则的评估器。"""

    evaluator_name = "rule_based_evaluator"
    evaluator_version = "rule-based-v1"

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        scores: list[EvaluationScore] = []
        final_answer = request.final_answer or (request.agent_state.final_answer if request.agent_state else None)
        events = request.events or (request.agent_state.events if request.agent_state else [])
        trajectory = summarize_events(events)
        output_text = _flatten_final_answer(final_answer)
        if request.mode in {"output", "combined"}:
            scores.extend(self._score_output(request=request, output_text=output_text))
        if request.mode in {"trajectory", "combined"}:
            scores.extend(self._score_trajectory(request=request, trajectory=trajectory, final_answer_text=output_text))
        scores = _filter_scores_for_output(scores=scores, request=request)
        total_score = _calculate_total_score(scores=scores, request=request)
        verdict = _score_to_verdict(total_score, request)
        return EvaluationResult(
            verdict=verdict,
            total_score=total_score,
            scores=scores,
            summary=_build_summary(verdict=verdict, total_score=total_score, trajectory=trajectory),
            strengths=_collect_strengths(scores),
            weaknesses=_collect_weaknesses(scores),
            suggestions=_collect_suggestions(scores, trajectory),
            evaluator_name=self.evaluator_name,
            evaluator_version=self.evaluator_version,
            mode=request.mode,
            trace_id=request.trace_id,
            run_id=request.run_id,
            metadata={"trajectory_summary": trajectory.model_dump()},
        )

    def _score_output(self, *, request: EvaluationRequest, output_text: str) -> list[EvaluationScore]:
        scores: list[EvaluationScore] = []
        final_answer = request.final_answer or (request.agent_state.final_answer if request.agent_state else None)
        summary_text = final_answer.summary.strip() if final_answer and final_answer.summary else ""
        has_output = bool(summary_text or output_text.strip())

        # 1. 先判断最终答案是否真的形成可评估输出，避免“没有答案却高分”的假阳性。
        not_empty = 1.0 if has_output else 0.0
        scores.append(
            EvaluationScore(
                dimension="completeness",
                score=not_empty,
                reason="最终答案存在非空 summary 或 output" if not_empty else "最终答案为空或缺失",
                evidence=[summary_text] if summary_text else [],
            )
        )

        # 2. 再处理 correctness。没有 expected_answer 时给中性分，不直接给满分。
        if not has_output:
            correctness_score = 0.0
            correctness_reason = "没有可评估的最终答案"
        elif request.expected_answer:
            expected_hit = _contains_all(output_text, [request.expected_answer])
            correctness_score = 1.0 if expected_hit else 0.5
            correctness_reason = "命中 expected_answer" if expected_hit else "未完全命中 expected_answer"
        else:
            correctness_score = 0.5
            correctness_reason = "未提供 expected_answer，按中性基线计分"
        scores.append(
            EvaluationScore(
                dimension="correctness",
                score=correctness_score,
                reason=correctness_reason,
                evidence=[request.expected_answer] if request.expected_answer else [],
            )
        )

        # 3. groundedness 只有在存在输出时才有意义；没有 reference_facts 时同样给中性分。
        fact_hits = [fact for fact in request.reference_facts if fact and fact in output_text]
        if not has_output:
            grounded_score = 0.0
            grounded_reason = "没有可用于对齐参考事实的最终答案"
        elif request.reference_facts:
            grounded_score = len(fact_hits) / len(request.reference_facts)
            grounded_reason = "参考事实命中率"
        else:
            grounded_score = 0.5
            grounded_reason = "未提供 reference_facts，按中性基线计分"
        scores.append(
            EvaluationScore(
                dimension="groundedness",
                score=round(grounded_score, 4),
                reason=grounded_reason,
                evidence=fact_hits,
            )
        )

        # 4. instruction_following 同理。没有 rubric 指令时给中性分，而不是直接满分。
        instructions = request.rubric.instructions if request.rubric else ""
        if not has_output:
            instruction_score = 0.0
            instruction_reason = "没有可用于判断指令遵循度的最终答案"
        elif instructions:
            instruction_score = 1.0 if instructions.lower() in output_text.lower() else 0.6
            instruction_reason = "rubric 指令命中" if instruction_score == 1.0 else "未直接体现 rubric 指令"
        else:
            instruction_score = 0.5
            instruction_reason = "未提供 rubric.instructions，按中性基线计分"
        scores.append(
            EvaluationScore(
                dimension="instruction_following",
                score=instruction_score,
                reason=instruction_reason,
                evidence=[instructions] if instructions else [],
            )
        )
        return scores

    def _score_trajectory(self, *, request: EvaluationRequest, trajectory: Any, final_answer_text: str) -> list[EvaluationScore]:
        scores: list[EvaluationScore] = []
        tool_effectiveness = 1.0
        if trajectory.total_tool_errors and final_answer_text:
            tool_effectiveness = 0.3
        elif trajectory.total_tool_errors:
            tool_effectiveness = 0.5
        scores.append(EvaluationScore(dimension="tool_effectiveness", score=tool_effectiveness, reason="工具失败但仍输出成功答案" if tool_effectiveness == 0.3 else "工具使用基本正常", evidence=trajectory.notes))
        efficiency = 1.0
        if trajectory.total_events > 12:
            efficiency = 0.6
        if trajectory.total_replans > 1:
            efficiency = min(efficiency, 0.5)
        scores.append(EvaluationScore(dimension="efficiency", score=efficiency, reason="事件数与 replan 次数控制良好" if efficiency == 1.0 else "轨迹偏长或重规划偏多", evidence=[f"events={trajectory.total_events}", f"replans={trajectory.total_replans}"]))
        memory_usefulness = 0.5
        all_events = request.events or (request.agent_state.events if request.agent_state else [])
        if any("memory" in str(getattr(event, "payload", {})).lower() for event in all_events):
            memory_usefulness = 1.0
        scores.append(EvaluationScore(dimension="memory_usefulness", score=memory_usefulness, reason="轨迹中出现 memory 相关使用痕迹" if memory_usefulness == 1.0 else "未观察到明确的 memory 使用痕迹", evidence=trajectory.notes))
        return scores


def _flatten_final_answer(final_answer: Any) -> str:
    if final_answer is None:
        return ""
    return f"{final_answer.summary}\n{json.dumps(final_answer.output, ensure_ascii=False, sort_keys=True)}"


def _contains_all(output_text: str, expected_parts: list[str]) -> bool:
    if not expected_parts:
        return True
    lowered = output_text.lower()
    return all(part.lower() in lowered for part in expected_parts if part)


def _score_to_verdict(score: float, request: EvaluationRequest) -> EvaluationVerdict:
    threshold = request.rubric.pass_threshold if request.rubric else 0.75
    if score >= threshold:
        return "pass"
    if score >= max(threshold - 0.25, 0.5):
        return "warning"
    return "fail"


def _build_summary(*, verdict: EvaluationVerdict, total_score: float, trajectory: Any) -> str:
    return f"规则评估完成，verdict={verdict}，score={total_score:.2f}，events={trajectory.total_events}，tool_errors={trajectory.total_tool_errors}"


def _collect_strengths(scores: list[EvaluationScore]) -> list[str]:
    return [f"{item.dimension} 表现稳定" for item in scores if item.score >= 0.8]


def _collect_weaknesses(scores: list[EvaluationScore]) -> list[str]:
    return [f"{item.dimension} 需要关注" for item in scores if item.score < 0.6]


def _collect_suggestions(scores: list[EvaluationScore], trajectory: Any) -> list[str]:
    suggestions: list[str] = []
    low_dimensions = [item.dimension for item in scores if item.score < 0.6]
    if "groundedness" in low_dimensions:
        suggestions.append("补充 reference_facts 或增强事实引用")
    if "tool_effectiveness" in low_dimensions:
        suggestions.append("检查工具失败后的降级与总结逻辑")
    if "efficiency" in low_dimensions:
        suggestions.append("减少无效步骤或限制 replan 次数")
    if trajectory.total_errors:
        suggestions.append("优先排查 error 事件对应的根因")
    return suggestions


def _filter_scores_for_output(*, scores: list[EvaluationScore], request: EvaluationRequest) -> list[EvaluationScore]:
    if not request.rubric or not request.rubric.dimensions:
        return scores
    allowed = set(request.rubric.dimensions)
    return [item for item in scores if item.dimension in allowed]
