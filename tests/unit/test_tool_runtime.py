"""Tool Runtime 组件测试。"""

from __future__ import annotations

import asyncio
import time

from agent_forge.components.protocol import ToolCall
from agent_forge.components.tool_runtime import (
    ToolChainStep,
    PythonMathTool,
    TavilySearchTool,
    ToolRuntime,
    ToolRuntimeError,
    ToolRuntimeEvent,
    ToolSpec,
    build_python_math_handler,
    build_tavily_search_handler,
)
from tests.unit.conftest import FakeTavilyClient


def test_tool_runtime_should_execute_successfully() -> None:
    runtime = ToolRuntime()
    runtime.register_tool(
        ToolSpec(
            name="echo",
            args_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
                "additionalProperties": False,
            },
        ),
        lambda args: {"echo": args["text"]},
    )
    result = runtime.execute(ToolCall(tool_call_id="tc_001", tool_name="echo", args={"text": "hello"}, principal="u1"))
    assert result.status == "ok"
    assert result.output["echo"] == "hello"


def test_tool_runtime_should_enforce_idempotency() -> None:
    runtime = ToolRuntime()
    call_counter = {"count": 0}

    def _counter_handler(_: dict) -> dict:
        call_counter["count"] += 1
        return {"count": call_counter["count"]}

    runtime.register_tool(ToolSpec(name="counter"), _counter_handler)
    call = ToolCall(tool_call_id="tc_same", tool_name="counter", args={}, principal="u1")
    first = runtime.execute(call)
    second = runtime.execute(call)

    assert first.status == "ok"
    assert second.status == "ok"
    assert first.output["count"] == 1
    assert second.output["count"] == 1
    assert call_counter["count"] == 1


def test_tool_runtime_should_validate_args_and_permissions() -> None:
    runtime = ToolRuntime()
    runtime.register_tool(
        ToolSpec(
            name="secured_tool",
            args_schema={
                "type": "object",
                "properties": {"x": {"type": "integer"}},
                "required": ["x"],
                "additionalProperties": False,
            },
            required_capabilities={"tool:run:secured"},
        ),
        lambda args: {"x": args["x"]},
    )

    missing_cap = runtime.execute(
        ToolCall(tool_call_id="tc_002", tool_name="secured_tool", args={"x": 1}, principal="u1"),
        capabilities=set(),
    )
    assert missing_cap.status == "error"
    assert missing_cap.error is not None
    assert missing_cap.error.error_code == "TOOL_PERMISSION_DENIED"

    bad_args = runtime.execute(
        ToolCall(tool_call_id="tc_003", tool_name="secured_tool", args={"x": "bad"}, principal="u1"),
        capabilities={"tool:run:secured"},
    )
    assert bad_args.status == "error"
    assert bad_args.error is not None
    assert bad_args.error.error_code == "TOOL_VALIDATION_ERROR"


def test_tool_runtime_should_mask_sensitive_fields_in_records() -> None:
    runtime = ToolRuntime()
    runtime.register_tool(
        ToolSpec(name="login", sensitive_fields={"password"}),
        lambda args: {"ok": True, "user": args.get("username", "")},
    )
    runtime.execute(
        ToolCall(
            tool_call_id="tc_004",
            tool_name="login",
            args={"username": "alice", "password": "secret"},
            principal="u1",
        )
    )
    records = runtime.get_records()
    assert len(records) == 1
    assert records[0].args_masked["password"] == "***"


def test_tool_runtime_should_return_timeout_error() -> None:
    runtime = ToolRuntime(default_timeout_ms=10, max_retries=0)
    runtime.register_tool(ToolSpec(name="slow_tool"), lambda _: _slow_response())

    result = runtime.execute(ToolCall(tool_call_id="tc_005", tool_name="slow_tool", args={}, principal="u1"))
    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "TOOL_TIMEOUT"
    records = runtime.get_records()
    assert len(records) == 1
    assert records[0].status == "error"


def test_python_math_tool_should_work_and_block_unsafe_expr() -> None:
    runtime = ToolRuntime()
    runtime.register_tool(
        ToolSpec(
            name="python_math",
            args_schema={"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
        ),
        build_python_math_handler(PythonMathTool()),
    )

    ok = runtime.execute(
        ToolCall(tool_call_id="tc_006", tool_name="python_math", args={"expression": "sqrt(9) + 2 * (3 + 1)"}, principal="u1")
    )
    assert ok.status == "ok"
    assert ok.output["value"] == 11.0

    blocked = runtime.execute(
        ToolCall(
            tool_call_id="tc_007",
            tool_name="python_math",
            args={"expression": "__import__('os').system('calc')"},
            principal="u1",
        )
    )
    assert blocked.status == "error"
    assert blocked.error is not None
    assert blocked.error.error_code == "TOOL_VALIDATION_ERROR"


def test_tavily_tool_should_work_with_mock_client() -> None:
    runtime = ToolRuntime()
    runtime.register_tool(
        ToolSpec(
            name="tavily_search",
            args_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"},
                    "search_depth": {"type": "string"},
                    "topic": {"type": "string"},
                },
                "required": ["query"],
            },
        ),
        build_tavily_search_handler(TavilySearchTool(client=FakeTavilyClient())),
    )
    result = runtime.execute(
        ToolCall(
            tool_call_id="tc_008",
            tool_name="tavily_search",
            args={"query": "agent runtime", "max_results": 2},
            principal="u1",
        )
    )
    assert result.status == "ok"
    assert result.output["result_count"] == 2
    assert result.output["results"][0]["title"] == "Doc1"


def test_tool_runtime_should_support_async_execute() -> None:
    runtime = ToolRuntime()

    async def _async_handler(args: dict) -> dict:
        await asyncio.sleep(0.01)
        return {"async_echo": args["value"]}

    runtime.register_tool(
        ToolSpec(name="async_echo", args_schema={"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]}),
        _async_handler,
    )

    async def _run() -> None:
        result = await runtime.execute_async(
            ToolCall(tool_call_id="tc_async_001", tool_name="async_echo", args={"value": "hello"}, principal="u1")
        )
        assert result.status == "ok"
        assert result.output["async_echo"] == "hello"

    asyncio.run(_run())


def test_tool_runtime_hooks_should_be_triggered() -> None:
    class _CaptureHooks:
        def __init__(self) -> None:
            self.events: list[str] = []
            self.after_called = False
            self.before_called = False
            self.error_called = False

        def before_execute(self, tool_call: ToolCall) -> ToolCall:
            self.before_called = True
            self.events.append("before_execute")
            return tool_call.model_copy(update={"args": {"text": "from_hook"}})

        def on_event(self, event: ToolRuntimeEvent) -> ToolRuntimeEvent | None:
            self.events.append(event.event_type)
            return event

        def after_execute(self, result):
            self.after_called = True
            self.events.append("after_execute")
            return result

        def on_error(self, error: ToolRuntimeError, tool_call: ToolCall) -> ToolRuntimeError:
            self.error_called = True
            self.events.append("on_error")
            return error

    hooks = _CaptureHooks()
    runtime = ToolRuntime(hooks=[hooks])
    runtime.register_tool(ToolSpec(name="echo"), lambda args: {"echo": args["text"]})

    ok = runtime.execute(ToolCall(tool_call_id="tc_hook_ok", tool_name="echo", args={"text": "raw"}, principal="u1"))
    assert ok.status == "ok"
    assert ok.output["echo"] == "from_hook"
    assert hooks.before_called is True
    assert hooks.after_called is True
    assert "before_execute" in hooks.events

    bad = runtime.execute(ToolCall(tool_call_id="tc_hook_bad", tool_name="missing", args={}, principal="u1"))
    assert bad.status == "error"
    assert hooks.error_called is True
    assert "on_error" in hooks.events


def test_tool_runtime_should_support_chain_calls() -> None:
    runtime = ToolRuntime()
    runtime.register_tool(ToolSpec(name="seed"), lambda _: {"value": 3})
    runtime.register_tool(ToolSpec(name="mul"), lambda args: {"value": args["left"] * args["right"]})

    chain = runtime.run_chain(
        chain_id="chain_001",
        steps=[
            ToolChainStep(step_id="step_seed", tool_name="seed"),
            ToolChainStep(
                step_id="step_mul",
                tool_name="mul",
                args={"right": 5},
                input_bindings={"left": "step_seed.value"},
            ),
        ],
        principal="u1",
    )
    assert chain["status"] == "ok"
    assert chain["outputs"]["step_mul"]["value"] == 15


def test_tool_runtime_should_support_execute_many_async() -> None:
    runtime = ToolRuntime()

    async def _async_double(args: dict) -> dict:
        await asyncio.sleep(0.01)
        return {"value": args["value"] * 2}

    runtime.register_tool(
        ToolSpec(
            name="async_double",
            args_schema={"type": "object", "properties": {"value": {"type": "integer"}}, "required": ["value"]},
        ),
        _async_double,
    )

    async def _run() -> None:
        calls = [
            ToolCall(tool_call_id="tc_batch_1", tool_name="async_double", args={"value": 1}, principal="u1"),
            ToolCall(tool_call_id="tc_batch_2", tool_name="async_double", args={"value": 2}, principal="u1"),
            ToolCall(tool_call_id="tc_batch_3", tool_name="async_double", args={"value": 3}, principal="u1"),
        ]
        results = await runtime.execute_many_async(calls, max_concurrency=2)
        assert [r.status for r in results] == ["ok", "ok", "ok"]
        # 必须与输入顺序一一对应。
        assert [r.output["value"] for r in results] == [2, 4, 6]

    asyncio.run(_run())


def test_tool_runtime_execute_many_async_should_validate_concurrency() -> None:
    runtime = ToolRuntime()

    async def _run() -> None:
        try:
            await runtime.execute_many_async([], max_concurrency=0)
            assert False, "should raise ValueError"
        except ValueError:
            assert True

    asyncio.run(_run())


def _slow_response() -> dict[str, bool]:
    time.sleep(0.05)
    return {"ok": True}
