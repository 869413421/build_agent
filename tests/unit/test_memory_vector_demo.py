"""Memory 向量示例测试。"""

from __future__ import annotations

from examples.memory.memory_vector_demo import run_vector_demo


def test_memory_vector_demo_should_write_and_read_back_records() -> None:
    result = run_vector_demo()

    assert result["written_count"] == 1
    assert result["vector_match_count"] == 1
    assert result["read_mode"] == "vector"
    assert any("偏好正式简洁结论前置" in item for item in result["matched_summaries"])
