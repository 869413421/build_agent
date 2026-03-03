"""DeepSeek demo script tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from agent_forge.components.model_runtime import ModelRuntime, StubDeepSeekAdapter


def _load_demo_module() -> ModuleType:
    demo_path = Path("examples/model_runtime/deepseek_demo.py").resolve()
    spec = importlib.util.spec_from_file_location("deepseek_demo", demo_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_deepseek_demo_non_stream_with_stub_runtime() -> None:
    demo = _load_demo_module()
    runtime = ModelRuntime(adapter=StubDeepSeekAdapter(mock_response='{"answer":"ok","confidence":0.95}'))

    result = demo.run_deepseek_once("hello", runtime=runtime)

    assert result["mode"] == "non-stream"
    assert result["parsed_output"] == {"answer": "ok", "confidence": 0.95}
    assert result["stats"]["total_tokens"] > 0


def test_deepseek_demo_stream_with_stub_runtime() -> None:
    demo = _load_demo_module()
    runtime = ModelRuntime(adapter=StubDeepSeekAdapter(mock_response='{"answer":"ok","confidence":0.95}'))

    result = demo.run_deepseek_stream("hello", runtime=runtime)

    assert result["mode"] == "stream"
    assert result["content"] == '{"answer":"ok","confidence":0.95}'
