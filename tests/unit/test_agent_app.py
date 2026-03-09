"""Tests for the `AgentApp` application-level registry and factory."""

from __future__ import annotations

import asyncio
from typing import Any

from agent_forge import Agent, AgentApp, AgentAppTool, AgentResult, AgentRunRequest
from agent_forge.components.engine import EngineLoop
from agent_forge.components.memory import MemoryReadResult, MemoryWriteResult
from agent_forge.components.model_runtime import ModelRequest, ModelResponse, ModelStats
from agent_forge.components.protocol import ToolCall
from agent_forge.components.tool_runtime import PythonMathTool, ToolSpec
from agent_forge.runtime.defaults import build_default_model_runtime


class RecordingEngineLoop(EngineLoop):
    """EngineLoop test double that proves custom loops can be injected."""

    def __init__(self) -> None:
        super().__init__()
        self.called = False

    async def arun(self, state, plan_fn, act_fn, reflect_fn=None, context=None):  # type: ignore[override]
        self.called = True
        return await super().arun(state, plan_fn, act_fn, reflect_fn, context)


class ToolAwareModelRuntime:
    """Model double that requests a single echo tool call before final answer."""

    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        _ = kwargs
        self.requests.append(request)
        if len(self.requests) == 1:
            return ModelResponse(
                content='{"summary": "need echo", "output": {}}',
                parsed_output={"summary": "need echo", "output": {}},
                tool_calls=[
                    ToolCall(
                        tool_call_id="tc_echo_1",
                        tool_name="echo",
                        args={"text": "hello"},
                        principal="agent",
                    )
                ],
                stats=ModelStats(total_tokens=10),
            )
        return ModelResponse(
            content='{"summary": "echo done", "output": {"answer": "hello"}}',
            parsed_output={"summary": "echo done", "output": {"answer": "hello"}},
            stats=ModelStats(total_tokens=12),
        )


class RecordingModelNameRuntime:
    """Model double that records selected model names."""

    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        _ = kwargs
        self.requests.append(request)
        return ModelResponse(
            content='{"summary": "named model", "output": {"answer": "ok"}}',
            parsed_output={"summary": "named model", "output": {"answer": "ok"}},
            stats=ModelStats(total_tokens=6),
        )


class RecordingMemoryRuntime:
    """Minimal memory runtime for app-level integration tests."""

    def __init__(self) -> None:
        self.read_queries: list[Any] = []
        self.write_requests: list[Any] = []

    def read(self, query):  # type: ignore[override]
        self.read_queries.append(query)
        return MemoryReadResult(records=[], total_matched=0, scope=query.scope)

    def write(self, request):  # type: ignore[override]
        self.write_requests.append(request)
        return MemoryWriteResult(records=[], trigger=request.trigger, trace_id=request.trace_id, run_id=request.run_id)


def test_agent_app_should_create_agent_and_run_minimal_flow() -> None:
    app = AgentApp()

    agent = app.create_agent(name="researcher", model="default")
    result = asyncio.run(agent.arun("最小运行"))

    assert isinstance(agent, Agent)
    assert agent.name == "researcher"
    assert result.status == "success"
    assert result.summary


def test_agent_app_should_support_allowed_tools_with_agent_scoped_tool_runtime() -> None:
    app = AgentApp()
    model_runtime = ToolAwareModelRuntime()
    app.register_model("tool-model", model_runtime)
    app.register_tools(
        [
            PythonMathTool(),
            AgentAppTool(
                spec=ToolSpec(
                    name="echo",
                    args_schema={
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                ),
                handler=lambda args: {"echo": args["text"]},
            ),
        ]
    )

    agent = app.create_agent(name="tool-agent", model="tool-model", allowed_tools=["echo"])
    result = asyncio.run(agent.arun("use echo"))

    assert result.status == "success"
    assert result.output["answer"] == "hello"
    assert result.metadata["tool_records"] == 1
    assert model_runtime.requests[0].tools is not None


def test_agent_app_should_default_to_empty_tool_permissions() -> None:
    app = AgentApp()
    app.register_tools([PythonMathTool()])

    agent = app.create_agent(name="no-tools", model="default")

    assert agent.runtime.tool_runtime.list_tool_specs() == []


def test_agent_app_should_raise_for_unknown_named_dependency() -> None:
    app = AgentApp()

    try:
        app.create_agent(name="bad-agent", model="missing")
        assert False, "should raise ValueError"
    except ValueError as exc:
        assert str(exc) == "未注册的model: missing"


def test_agent_app_should_raise_for_unknown_allowed_tool() -> None:
    app = AgentApp()

    try:
        app.create_agent(name="bad-agent", model="default", allowed_tools=["missing_tool"])
        assert False, "should raise ValueError"
    except ValueError as exc:
        assert str(exc) == "未注册的tool: missing_tool"


def test_agent_app_should_support_memory_registration_and_runtime_injection() -> None:
    app = AgentApp()
    memory_runtime = RecordingMemoryRuntime()
    app.register_memory("default", memory_runtime)

    agent = app.create_agent(name="memory-agent", model="default", memory="default")
    result = asyncio.run(
        agent.arun(
            "remember me",
            tenant_id="tenant_a",
            user_id="user_a",
        )
    )

    assert result.status == "success"
    assert len(memory_runtime.read_queries) == 1
    assert len(memory_runtime.write_requests) == 1


def test_agent_app_should_reject_invalid_memory_runtime_shape() -> None:
    app = AgentApp()

    try:
        app.register_memory("bad", object())
        assert False, "should raise TypeError"
    except TypeError as exc:
        assert "memory runtime" in str(exc)


def test_agent_app_should_support_custom_agent_cls_and_engine_loop() -> None:
    engine_loop = RecordingEngineLoop()

    class CustomAgent(Agent):
        def _after_run(self, request: AgentRunRequest, result: AgentResult) -> AgentResult:
            result.metadata["agent_name"] = self.name
            return result

    app = AgentApp()

    agent = app.create_agent(
        name="custom-agent",
        model="default",
        agent_cls=CustomAgent,
        engine_loop=engine_loop,
    )
    result = asyncio.run(agent.arun("custom agent and engine loop"))

    assert isinstance(agent, CustomAgent)
    assert engine_loop.called is True
    assert result.metadata["agent_name"] == "custom-agent"


def test_agent_app_should_allow_registering_additional_model_names() -> None:
    app = AgentApp()
    custom_model = RecordingModelNameRuntime()
    app.register_model("custom", custom_model)

    agent = app.create_agent(name="custom-model-agent", model="custom")
    result = asyncio.run(agent.arun("use custom"))

    assert agent.name == "custom-model-agent"
    assert result.status == "success"
    assert custom_model.requests[0].model == "custom"


def test_agent_app_should_allow_overriding_default_model_registration() -> None:
    app = AgentApp()
    replacement = build_default_model_runtime()

    app.register_model("default", replacement)

    assert app._models["default"] is replacement
