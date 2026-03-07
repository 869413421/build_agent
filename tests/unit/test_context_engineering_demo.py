"""Context Engineering 示例脚本测试。"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_demo_module():
    """按文件路径加载 examples 脚本，避免把 examples 目录当成包。"""

    file_path = Path("examples/context_engineering/context_engineering_demo.py")
    spec = importlib.util.spec_from_file_location("context_engineering_demo", file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 context_engineering_demo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_context_engineering_demo_should_show_trimmed_request() -> None:
    """示例脚本应展示被 Hook 改写后的最终请求。"""

    result = _load_demo_module().run_demo()

    assert result["response_content"] == '{"status":"ok","message":"context engineered"}'
    assert result["final_tools"][0]["function"]["name"] == "search_policy"
    assert any(item["role"] == "developer" for item in result["final_messages"])
    assert result["budget_report"]["available_tokens"] > 0
    assert "citations_dropped" in result["budget_report"]["dropped_sections"]


def test_context_engineering_demo_should_drop_old_history_under_budget() -> None:
    """示例脚本应体现旧历史让位给关键上下文。"""

    result = _load_demo_module().run_demo()
    contents = [item["content"] for item in result["final_messages"]]

    assert not any("old-question-" in item for item in contents)
    assert any("latest-user-" in item for item in contents)
