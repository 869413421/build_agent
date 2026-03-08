"""Memory bridge example 测试。"""

from __future__ import annotations

from examples.memory.memory_bridge_demo import run_bridge_demo


def test_memory_bridge_demo_should_convert_records_into_context_messages() -> None:
    result = run_bridge_demo()

    assert result["record_count"] == 2
    assert result["message_count"] == 2
    assert result["message_roles"] == ["developer", "developer"]
    assert "[记忆][" in result["first_message"]
    assert any(label in result["first_message"] for label in ["[记忆][session/summary]", "[记忆][long_term/preference]"])
