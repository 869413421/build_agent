"""Evaluator 运行时。"""

from __future__ import annotations

from typing import Any

from agent_forge.components.evaluator.domain import (
    EvaluationRequest,
    EvaluationResult,
    EvaluationScore,
    EvaluationVerdict,
    Evaluator,
    TrajectorySummary,
)


class EvaluatorRuntime:
    """统一编排规则评估与 LLM judge。"""

    def __init__(self, *, evaluators: list[Evaluator]) -> None:
        self._evaluators = evaluators

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        results = [evaluator.evaluate(request) for evaluator in self._evaluators]
        if not results:
            raise ValueError("EvaluatorRuntime 至少需要一个 evaluator")
        if len(results) == 1:
            return results[0]
        return _aggregate_results(results=results, request=request)

    def evaluate_output(self, request: EvaluationRequest) -> EvaluationResult:
        return self.evaluate(request.model_copy(update={"mode": "output"}))

    def evaluate_trajectory(self, request: EvaluationRequest) -> EvaluationResult:
        return self.evaluate(request.model_copy(update={"mode": "trajectory"}))

    def evaluate_combined(self, request: EvaluationRequest) -> EvaluationResult:
        return self.evaluate(request.model_copy(update={"mode": "combined"}))

    def compare(self, results: list[EvaluationResult]) -> dict[str, Any]:
        if not results:
            return {"winner": None, "ranking": [], "score_gap": 0.0}
        ranking = sorted(results, key=lambda item: item.total_score, reverse=True)
        winner = ranking[0]
        runner_up = ranking[1] if len(ranking) > 1 else None
        return {
            "winner": _build_candidate_entry(result=winner, index=0),
            "winner_summary": winner.summary,
            "ranking": [_build_candidate_entry(result=item, index=index) for index, item in enumerate(ranking)],
            "score_gap": round(winner.total_score - (runner_up.total_score if runner_up else 0.0), 4),
        }

    def summarize_events(self, events: list[object]) -> TrajectorySummary:
        return summarize_events(events)


def summarize_events(events: list[object]) -> TrajectorySummary:
    total_tool_calls = 0
    total_tool_errors = 0
    total_errors = 0
    total_replans = 0
    seen_replan_revisions: set[int] = set()
    event_types: list[str] = []
    notes: list[str] = []
    for event in events:
        event_type = getattr(event, "event_type", "")
        payload = getattr(event, "payload", {}) or {}
        event_types.append(event_type)
        if event_type == "tool_call":
            total_tool_calls += 1
        if event_type == "tool_result" and payload.get("status") == "error":
            total_tool_errors += 1
        if event_type == "error":
            total_errors += 1
        if payload.get("plan_revision", 0) and payload.get("plan_origin") == "replan":
            seen_replan_revisions.add(int(payload["plan_revision"]))
        if payload.get("replan_count"):
            total_replans = max(total_replans, int(payload["replan_count"]))
    total_replans = max(total_replans, len(seen_replan_revisions))
    if total_tool_errors:
        notes.append("轨迹中出现工具失败")
    if total_replans:
        notes.append("轨迹中出现计划修订")
    return TrajectorySummary(
        total_events=len(events),
        total_tool_calls=total_tool_calls,
        total_tool_errors=total_tool_errors,
        total_replans=total_replans,
        total_errors=total_errors,
        unique_event_types=sorted(set(event_types)),
        notes=notes,
    )


def _aggregate_results(*, results: list[EvaluationResult], request: EvaluationRequest) -> EvaluationResult:
    merged_scores = _filter_scores_by_rubric(scores=_aggregate_scores_by_dimension(results), request=request)
    strengths: list[str] = []
    weaknesses: list[str] = []
    suggestions: list[str] = []
    for result in results:
        strengths.extend(result.strengths)
        weaknesses.extend(result.weaknesses)
        suggestions.extend(result.suggestions)
    avg_score = _calculate_total_score(scores=merged_scores, request=request)
    verdict = _score_to_verdict(avg_score, request)
    return EvaluationResult(
        verdict=verdict,
        total_score=avg_score,
        scores=merged_scores,
        summary=f"聚合了 {len(results)} 个 evaluator 的结果",
        strengths=_dedupe(strengths),
        weaknesses=_dedupe(weaknesses),
        suggestions=_dedupe(suggestions),
        evaluator_name="aggregated_evaluator",
        evaluator_version="aggregated-v1",
        mode=request.mode,
        trace_id=request.trace_id,
        run_id=request.run_id,
        metadata={
            "source_evaluators": [item.evaluator_name for item in results],
            "aggregated_dimensions": [item.dimension for item in merged_scores],
        },
    )


def _score_to_verdict(score: float, request: EvaluationRequest) -> EvaluationVerdict:
    threshold = request.rubric.pass_threshold if request.rubric else 0.75
    if score >= threshold:
        return "pass"
    if score >= max(threshold - 0.25, 0.5):
        return "warning"
    return "fail"


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _build_candidate_entry(*, result: EvaluationResult, index: int) -> dict[str, Any]:
    return {
        "candidate_id": _candidate_id(result=result, index=index),
        "trace_id": result.trace_id,
        "run_id": result.run_id,
        "evaluator": result.evaluator_name,
        "mode": result.mode,
        "score": result.total_score,
        "verdict": result.verdict,
    }


def _candidate_id(*, result: EvaluationResult, index: int) -> str:
    if result.trace_id and result.run_id:
        return f"{result.trace_id}:{result.run_id}"
    if result.run_id:
        return f"run:{result.run_id}"
    if result.trace_id:
        return f"trace:{result.trace_id}"
    return f"{result.evaluator_name}:{result.mode}:{index}"


def _calculate_total_score(*, scores: list[EvaluationScore], request: EvaluationRequest) -> float:
    active_scores = _filter_scores_by_rubric(scores=scores, request=request)
    if not active_scores:
        return 0.0
    weights = _build_weight_map(active_scores=active_scores, request=request)
    weighted_sum = sum(item.score * weights[item.dimension] for item in active_scores)
    total_weight = sum(weights[item.dimension] for item in active_scores)
    return round(weighted_sum / total_weight, 4) if total_weight else 0.0


def _filter_scores_by_rubric(*, scores: list[EvaluationScore], request: EvaluationRequest) -> list[EvaluationScore]:
    if not request.rubric or not request.rubric.dimensions:
        return scores
    allowed = set(request.rubric.dimensions)
    return [item for item in scores if item.dimension in allowed]


def _build_weight_map(*, active_scores: list[EvaluationScore], request: EvaluationRequest) -> dict[str, float]:
    configured = request.rubric.weights if request.rubric else {}
    weights: dict[str, float] = {}
    for item in active_scores:
        raw_weight = configured.get(item.dimension, 1.0)
        weights[item.dimension] = raw_weight if raw_weight > 0 else 1.0
    return weights


def _aggregate_scores_by_dimension(results: list[EvaluationResult]) -> list[EvaluationScore]:
    grouped: dict[str, list[EvaluationScore]] = {}
    for result in results:
        for score in result.scores:
            grouped.setdefault(score.dimension, []).append(score)

    aggregated: list[EvaluationScore] = []
    for dimension, dimension_scores in grouped.items():
        avg_score = round(sum(item.score for item in dimension_scores) / len(dimension_scores), 4)
        reasons = _dedupe([item.reason for item in dimension_scores])
        evidence = _dedupe([e for item in dimension_scores for e in item.evidence])
        aggregated.append(
            EvaluationScore(
                dimension=dimension,  # type: ignore[arg-type]
                score=avg_score,
                reason="；".join(reasons),
                evidence=evidence,
            )
        )
    return sorted(aggregated, key=lambda item: item.dimension)
