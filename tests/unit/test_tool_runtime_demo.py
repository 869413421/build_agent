"""Tool runtime demo script tests."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from types import ModuleType

from agent_forge.components.tool_runtime import TavilySearchTool, ToolSpec
from tests.unit.conftest import FakeTavilyClient

# L-2 修复：基于 __file__ 计算示例路径，不再依赖当前工作目录。
_DEMO_PATH = Path(__file__).parent.parent.parent / "examples" / "tool_runtime" / "tool_runtime_demo.py"


def _load_demo_module() -> ModuleType:
    demo_path = _DEMO_PATH.resolve()
    spec = importlib.util.spec_from_file_location("tool_runtime_demo", demo_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tool_runtime_demo_math_once_success() -> None:
    demo = _load_demo_module()
    runtime = demo.create_demo_runtime(tavily_tool=TavilySearchTool(client=FakeTavilyClient()))

    result = demo.run_math_once("sqrt(16) + 2**3", runtime=runtime)

    assert result["status"] == "ok"
    assert result["output"]["value"] == 12.0


def test_tool_runtime_demo_math_once_invalid_expression() -> None:
    demo = _load_demo_module()
    runtime = demo.create_demo_runtime(tavily_tool=TavilySearchTool(client=FakeTavilyClient()))

    result = demo.run_math_once("__import__('os').system('calc')", runtime=runtime)

    assert result["status"] == "error"
    assert result["error"]["error_code"] == "TOOL_VALIDATION_ERROR"


def test_tool_runtime_demo_tavily_once_with_fake_client() -> None:
    demo = _load_demo_module()
    runtime = demo.create_demo_runtime(tavily_tool=TavilySearchTool(client=FakeTavilyClient()))

    result = demo.run_tavily_once("agent runtime", max_results=2, runtime=runtime)

    assert result["status"] == "ok"
    assert result["output"]["result_count"] == 2
    assert result["output"]["results"][0]["title"] == "Doc1"


def test_tool_runtime_demo_math_batch_async() -> None:
    demo = _load_demo_module()
    runtime = demo.create_demo_runtime(tavily_tool=TavilySearchTool(client=FakeTavilyClient()))

    batch = asyncio.run(demo.run_math_batch_async(["1+1", "2+2", "3+3"], runtime=runtime, max_concurrency=2))

    assert len(batch) == 3
    assert [item["status"] for item in batch] == ["ok", "ok", "ok"]
    assert [item["output"]["value"] for item in batch] == [2.0, 4.0, 6.0]


def test_tool_runtime_demo_math_batch_async_should_keep_order() -> None:
    demo = _load_demo_module()
    runtime = demo.create_demo_runtime(tavily_tool=TavilySearchTool(client=FakeTavilyClient()))

    batch = asyncio.run(demo.run_math_batch_async(["10-1", "10-2", "10-3"], runtime=runtime, max_concurrency=3))

    assert [item["tool_call_id"] for item in batch] == [
        "demo_math_batch_1",
        "demo_math_batch_2",
        "demo_math_batch_3",
    ]
    assert [item["output"]["value"] for item in batch] == [9.0, 8.0, 7.0]


def test_tool_runtime_demo_chain_once_success() -> None:
    demo = _load_demo_module()
    runtime = demo.create_demo_runtime(tavily_tool=TavilySearchTool(client=FakeTavilyClient()))

    chain = demo.run_tool_chain_once(runtime=runtime)

    assert chain["status"] == "ok"
    assert chain["outputs"]["step_seed"]["value"] == 6
    assert chain["outputs"]["step_mul"]["value"] == 42


def test_tool_runtime_demo_chain_should_stop_on_error() -> None:
    demo = _load_demo_module()
    runtime = demo.create_demo_runtime(tavily_tool=TavilySearchTool(client=FakeTavilyClient()))
    runtime.register_tool(ToolSpec(name="seed"), lambda _: {"value": 2})
    runtime.register_tool(ToolSpec(name="explode"), lambda _: (_ for _ in ()).throw(RuntimeError("boom")))
    runtime.register_tool(ToolSpec(name="never"), lambda _: {"value": 999})

    chain = runtime.run_chain(
        chain_id="chain_fail_demo",
        steps=[
            demo.ToolChainStep(step_id="s1", tool_name="seed"),
            demo.ToolChainStep(step_id="s2", tool_name="explode"),
            demo.ToolChainStep(step_id="s3", tool_name="never"),
        ],
        principal="demo",
    )

    assert chain["status"] == "error"
    assert "s1" in chain["outputs"]
    assert "s2" in chain["outputs"]  # error output defaults {}
    assert "s3" not in chain["outputs"]
