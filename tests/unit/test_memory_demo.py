"""Memory 示例测试。"""

from __future__ import annotations

from examples.memory.memory_demo import run_demo


def test_memory_demo_should_return_written_records() -> None:
    result = run_demo()

    assert result["written_count"] == 2
    assert any("CEO 周报请求" in item for item in result["session_records"])


def test_memory_demo_should_keep_long_term_records_even_without_chroma_dependency() -> None:
    result = run_demo()

    assert isinstance(result["vector_status"], str)
    assert any("偏好简洁要点式" in item for item in result["long_term_records"])
