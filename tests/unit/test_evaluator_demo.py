"""Evaluator 示例测试。"""

from __future__ import annotations

from examples.evaluator.evaluator_demo import run_demo


def test_evaluator_demo_should_return_structured_summary() -> None:
    result = run_demo()
    assert result["verdict"] in {"pass", "warning"}
    assert result["total_score"] > 0.0
    assert result["score_count"] >= 2
