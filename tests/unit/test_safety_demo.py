"""Safety 示例测试。"""

from __future__ import annotations

from examples.safety.safety_demo import run_demo


def test_safety_demo_should_show_three_stage_decisions() -> None:
    result = run_demo()

    assert result["input_action"] == "allow"
    assert result["denied_tool_status"] == "error"
    assert result["allowed_tool_status"] == "ok"
    assert result["output_action"] == "downgrade"
    assert result["safe_answer_status"] == "partial"
    assert result["audit_count"] >= 2
