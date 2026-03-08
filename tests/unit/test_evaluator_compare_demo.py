"""Evaluator 对比示例测试。"""

from __future__ import annotations

from examples.evaluator.evaluator_compare_demo import run_compare_demo


def test_evaluator_compare_demo_should_return_ranking() -> None:
    result = run_compare_demo()
    assert result["winner"]["run_id"] == "run_good"
    assert result["winner"]["evaluator"] == "rule_based_evaluator"
    assert len(result["ranking"]) == 2
    assert result["score_gap"] >= 0.0
