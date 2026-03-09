"""Tests for `AgentRuntime` orchestration and extension points."""

from __future__ import annotations

import asyncio
from typing import Any

from agent_forge.components.engine import EngineLoop
from agent_forge.components.memory import MemoryReadResult, MemoryRecord, MemorySource, MemoryWriteResult
from agent_forge.components.model_runtime import ModelRequest, ModelResponse, ModelStats
from agent_forge.components.protocol import ErrorInfo, ToolCall
from agent_forge.components.retrieval import RetrievedCitation, RetrievalResult
from agent_forge.components.safety import SafetyCheckRequest, SafetyDecision, SafetyRuntime
from agent_forge.components.tool_runtime import ToolRuntime, ToolSpec
from agent_forge.runtime.runtime import AgentRuntime
from agent_forge.runtime.schemas import AgentRunRequest


class DenyInputReviewer:
    """Test reviewer that always blocks input."""

    reviewer_name = "deny_input"
    reviewer_version = "test-v1"
    policy_version = "policy-test"
    stage = "input"

    def review(self, request: SafetyCheckRequest) -> SafetyDecision:
        return SafetyDecision(
            allowed=False,
            action="deny",
            stage=request.stage,
            reason="input blocked by test reviewer",
            reviewer_name=self.reviewer_name,
            reviewer_version=self.reviewer_version,
            policy_version=self.policy_version,
        )


class PassThroughReviewer:
    """Test reviewer that always allows requests."""

    reviewer_name = "pass_through"
    reviewer_version = "test-v1"
    policy_version = "policy-test"
    stage = "input"

    def __init__(self, stage: str) -> None:
        self.stage = stage

    def review(self, request: SafetyCheckRequest) -> SafetyDecision:
        return SafetyDecision(
            allowed=True,
            action="allow",
            stage=request.stage,
            reason="allowed",
            reviewer_name=self.reviewer_name,
            reviewer_version=self.reviewer_version,
            policy_version=self.policy_version,
        )


class DowngradeOutputReviewer:
    """Test reviewer that always downgrades output."""

    reviewer_name = "downgrade_output"
    reviewer_version = "test-v1"
    policy_version = "policy-test"
    stage = "output"

    def review(self, request: SafetyCheckRequest) -> SafetyDecision:
        return SafetyDecision(
            allowed=False,
            action="downgrade",
            stage=request.stage,
            reason="output downgraded by test reviewer",
            reviewer_name=self.reviewer_name,
            reviewer_version=self.reviewer_version,
            policy_version=self.policy_version,
        )


class RecordingEngineLoop(EngineLoop):
    """EngineLoop test double that proves custom loops can be injected."""

    def __init__(self) -> None:
        super().__init__()
        self.called = False

    async def arun(self, state, plan_fn, act_fn, reflect_fn=None, context=None):  # type: ignore[override]
        self.called = True
        return await super().arun(state, plan_fn, act_fn, reflect_fn, context)


class RecordingRetrievalRuntime:
    """Retrieval test double that records the normalized query object."""

    def __init__(self) -> None:
        self.last_query = None

    def search(self, query):  # type: ignore[override]
        self.last_query = query
        return RetrievalResult(
            hits=[],
            citations=[
                RetrievedCitation(
                    document_id="doc-1",
                    title="retrieved-doc",
                    source_uri="memory://doc-1",
                    snippet="retrieved snippet",
                )
            ],
            backend_name="test-backend",
            retriever_version="v1",
            reranker_version="v1",
            total_candidates=1,
        )


class ToolCallingModelRuntime:
    """First request emits tool calls, second request emits final answer."""

    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        _ = kwargs
        self.requests.append(request)
        if len(self.requests) == 1:
            return ModelResponse(
                content='{"summary": "need tool", "output": {}}',
                parsed_output={"summary": "need tool", "output": {}},
                tool_calls=[
                    ToolCall(
                        tool_call_id="tc_calc_1",
                        tool_name="calculator",
                        args={"expression": "1 + 2"},
                        principal="agent",
                    )
                ],
                stats=ModelStats(total_tokens=12),
            )
        return ModelResponse(
            content='{"summary": "tool summary", "output": {"answer": "3"}, "references": ["model:final"]}',
            parsed_output={
                "summary": "tool summary",
                "output": {"answer": "3"},
                "references": ["model:final"],
            },
            stats=ModelStats(total_tokens=18),
        )


class ReusableToolCallingModelRuntime:
    """Model double that alternates between tool planning and final answer."""

    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        _ = kwargs
        self.requests.append(request)
        if len(self.requests) % 2 == 1:
            return ModelResponse(
                content='{"summary": "need tool", "output": {}}',
                parsed_output={"summary": "need tool", "output": {}},
                tool_calls=[
                    ToolCall(
                        tool_call_id=f"tc_calc_{len(self.requests)}",
                        tool_name="calculator",
                        args={"expression": "1 + 2"},
                        principal="agent",
                    )
                ],
                stats=ModelStats(total_tokens=12),
            )
        return ModelResponse(
            content='{"summary": "tool summary", "output": {"answer": "3"}, "references": ["model:final"]}',
            parsed_output={
                "summary": "tool summary",
                "output": {"answer": "3"},
                "references": ["model:final"],
            },
            stats=ModelStats(total_tokens=18),
        )


class PhaseAwareToolCallingModelRuntime:
    """根据请求阶段返回工具规划或最终答案，便于并发复用同一个 runtime。"""

    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        _ = kwargs
        self.requests.append(request)
        task_text = next((message.content for message in reversed(request.messages) if message.role == "user"), "default")
        normalized = str(task_text).replace(" ", "_")
        if request.tools:
            return ModelResponse(
                content='{"summary": "need tool", "output": {}}',
                parsed_output={"summary": "need tool", "output": {}},
                tool_calls=[
                    ToolCall(
                        tool_call_id=f"tc_{normalized}",
                        tool_name="calculator",
                        args={"expression": "1 + 2"},
                        principal="agent",
                    )
                ],
                stats=ModelStats(total_tokens=10),
            )
        return ModelResponse(
            content=f'{{"summary": "tool summary {normalized}", "output": {{"answer": "3"}}}}',
            parsed_output={"summary": f"tool summary {normalized}", "output": {"answer": "3"}},
            stats=ModelStats(total_tokens=12),
        )


class RecordingModelRuntime:
    """Model double that only records requests and returns a fixed answer."""

    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        _ = kwargs
        self.requests.append(request)
        return ModelResponse(
            content='{"summary": "plain summary", "output": {"answer": "ok"}}',
            parsed_output={"summary": "plain summary", "output": {"answer": "ok"}},
            stats=ModelStats(total_tokens=8),
        )


class RecordingModelNameRuntime:
    """Model double that records the incoming `request.model` value."""

    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        _ = kwargs
        self.requests.append(request)
        return ModelResponse(
            content='{"summary": "named model", "output": {"model": "ok"}}',
            parsed_output={"summary": "named model", "output": {"model": "ok"}},
            stats=ModelStats(total_tokens=6),
        )


class ContentOnlyJsonModelRuntime:
    """Model double that only returns JSON in `content`."""

    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        _ = kwargs
        self.requests.append(request)
        return ModelResponse(
            content='{"summary": "json only", "output": {"answer": "from-content"}}',
            parsed_output=None,
            stats=ModelStats(total_tokens=5),
        )


class PlainTextModelRuntime:
    """Model double that only returns plain text content."""

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        _ = request
        _ = kwargs
        return ModelResponse(
            content="plain text answer",
            parsed_output=None,
            stats=ModelStats(total_tokens=4),
        )


class RecordingMemoryRuntime:
    """Minimal memory runtime test double."""

    def __init__(self) -> None:
        self.read_queries: list[Any] = []
        self.write_requests: list[Any] = []

    def read(self, query):  # type: ignore[override]
        self.read_queries.append(query)
        return MemoryReadResult(
            records=[
                MemoryRecord(
                    record_key="user_pref",
                    scope="long_term",
                    tenant_id=query.tenant_id,
                    user_id=query.user_id,
                    session_id=None,
                    category="preference",
                    content="用户喜欢结构化输出",
                    summary="喜欢结构化输出",
                    metadata={},
                    source=MemorySource(source_type="agent_message"),
                )
            ],
            total_matched=1,
            scope=query.scope,
        )

    def write(self, request):  # type: ignore[override]
        self.write_requests.append(request)
        return MemoryWriteResult(
            records=[],
            trigger=request.trigger,
            trace_id=request.trace_id,
            run_id=request.run_id,
        )


class CountingMemoryRuntime:
    """Memory runtime double that reports formal write counters without returning records."""

    def __init__(self) -> None:
        self.write_requests: list[Any] = []

    def read(self, query):  # type: ignore[override]
        return MemoryReadResult(records=[], total_matched=0, scope=query.scope)

    def write(self, request):  # type: ignore[override]
        self.write_requests.append(request)
        if request.trigger == "finish":
            return MemoryWriteResult(
                records=[],
                structured_written_count=2,
                vector_written_count=0,
                trigger=request.trigger,
                trace_id=request.trace_id,
                run_id=request.run_id,
            )
        return MemoryWriteResult(
            records=[],
            structured_written_count=1,
            vector_written_count=1,
            trigger=request.trigger,
            trace_id=request.trace_id,
            run_id=request.run_id,
        )


def test_agent_runtime_should_block_denied_input_before_engine() -> None:
    runtime = AgentRuntime(
        safety_runtime=SafetyRuntime(
            input_reviewer=DenyInputReviewer(),
            tool_reviewer=PassThroughReviewer("tool"),
            output_reviewer=PassThroughReviewer("output"),
        )
    )

    result = asyncio.run(runtime.arun(AgentRunRequest(task_input="blocked")))

    assert result.status == "blocked"
    assert result.error is not None
    assert result.error.error_code == "AGENT_INPUT_BLOCKED"


def test_agent_runtime_should_apply_output_safety_downgrade() -> None:
    runtime = AgentRuntime(
        safety_runtime=SafetyRuntime(
            input_reviewer=PassThroughReviewer("input"),
            tool_reviewer=PassThroughReviewer("tool"),
            output_reviewer=DowngradeOutputReviewer(),
        )
    )

    result = asyncio.run(runtime.arun(AgentRunRequest(task_input="normal request")))

    assert result.status == "partial"
    assert result.final_answer is not None
    assert result.final_answer.status == "partial"
    assert result.output["safety_action"] == "downgrade"


def test_agent_runtime_should_pass_capabilities_into_result_metadata() -> None:
    runtime = AgentRuntime()

    result = asyncio.run(
        runtime.arun(
            AgentRunRequest(
                task_input="capability request",
                capabilities={"safety:tool:high_risk", "agent:debug"},
            )
        )
    )

    assert result.metadata["capabilities"] == ["agent:debug", "safety:tool:high_risk"]


def test_agent_runtime_should_allow_custom_engine_loop_injection() -> None:
    engine_loop = RecordingEngineLoop()
    runtime = AgentRuntime(engine_loop=engine_loop)

    result = asyncio.run(runtime.arun(AgentRunRequest(task_input="custom engine loop")))

    assert engine_loop.called is True
    assert result.status == "success"


def test_agent_runtime_should_allow_subclass_runtime_override() -> None:
    class CustomRuntime(AgentRuntime):
        def _build_final_answer(self, *, normalized, state):  # type: ignore[override]
            answer = super()._build_final_answer(normalized=normalized, state=state)
            answer.summary = f"custom:{answer.summary}"
            return answer

    result = asyncio.run(CustomRuntime().arun(AgentRunRequest(task_input="custom runtime")))

    assert result.summary.startswith("custom:")


def test_agent_runtime_should_preserve_requested_trace_id() -> None:
    runtime = AgentRuntime()

    result = asyncio.run(runtime.arun(AgentRunRequest(task_input="trace request", trace_id="trace_manual")))

    assert result.trace_id == "trace_manual"
    assert result.session_id.startswith("session_")


def test_agent_runtime_should_use_normalized_retrieval_query_and_merge_references() -> None:
    retrieval_runtime = RecordingRetrievalRuntime()
    runtime = AgentRuntime(retrieval_runtime=retrieval_runtime)

    result = asyncio.run(
        runtime.arun(
            AgentRunRequest(
                task_input="use retrieval",
                context={"retrieval_query": " retrieval context "},
            )
        )
    )

    assert retrieval_runtime.last_query is not None
    assert retrieval_runtime.last_query.query_text == "retrieval context"
    assert any(item.startswith("retrieval:") for item in result.references)


def test_agent_runtime_should_execute_model_tool_calls_via_tool_runtime() -> None:
    model_runtime = ToolCallingModelRuntime()
    tool_runtime = ToolRuntime()
    tool_runtime.register_tool(
        ToolSpec(
            name="calculator",
            args_schema={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        ),
        lambda args: {"result": 3 if str(args["expression"]).replace(" ", "") == "1+2" else 0},
    )
    runtime = AgentRuntime(model_runtime=model_runtime, tool_runtime=tool_runtime)

    result = asyncio.run(runtime.arun(AgentRunRequest(task_input="calculate 1 + 2")))

    assert result.status == "success"
    assert result.output["answer"] == "3"
    assert result.metadata["tool_records"] == 1
    assert model_runtime.requests[0].tools is not None
    assert model_runtime.requests[1].tools is None


def test_agent_runtime_should_abort_when_tool_runtime_returns_error() -> None:
    model_runtime = ToolCallingModelRuntime()
    tool_runtime = ToolRuntime()
    runtime = AgentRuntime(model_runtime=model_runtime, tool_runtime=tool_runtime)

    result = asyncio.run(runtime.arun(AgentRunRequest(task_input="calculate 1 + 2")))

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.error_code == "TOOL_NOT_FOUND"
    assert result.final_answer is not None
    assert result.final_answer.status == "failed"
    assert result.metadata["tool_records"] == 1


def test_agent_runtime_should_read_and_write_memory_when_runtime_is_configured() -> None:
    memory_runtime = RecordingMemoryRuntime()
    model_runtime = RecordingModelRuntime()
    runtime = AgentRuntime(memory_runtime=memory_runtime, model_runtime=model_runtime)

    result = asyncio.run(
        runtime.arun(
            AgentRunRequest(
                task_input="remember me",
                tenant_id="tenant_a",
                user_id="user_a",
            )
        )
    )

    assert result.status == "success"
    assert result.metadata["memory_read_count"] == 1
    assert result.metadata["memory_write_count"] == 0
    assert len(memory_runtime.read_queries) == 1
    assert len(memory_runtime.write_requests) == 1
    assert memory_runtime.write_requests[0].trigger == "finish"
    assert any(message.metadata.get("memory_id") for message in model_runtime.requests[0].messages)


def test_agent_runtime_should_use_explicit_model_name_in_model_request() -> None:
    model_runtime = RecordingModelNameRuntime()
    runtime = AgentRuntime(model_runtime=model_runtime, model_name="custom-model")

    result = asyncio.run(runtime.arun(AgentRunRequest(task_input="use custom model")))

    assert result.status == "success"
    assert model_runtime.requests[0].model == "custom-model"


def test_agent_runtime_should_fallback_to_json_content_when_parsed_output_is_missing() -> None:
    runtime = AgentRuntime(model_runtime=ContentOnlyJsonModelRuntime())

    result = asyncio.run(runtime.arun(AgentRunRequest(task_input="json only content")))

    assert result.status == "success"
    assert result.summary == "json only"
    assert result.output == {"answer": "from-content"}


def test_agent_runtime_should_fallback_to_plain_text_content_when_no_structured_payload_exists() -> None:
    runtime = AgentRuntime(model_runtime=PlainTextModelRuntime())

    result = asyncio.run(runtime.arun(AgentRunRequest(task_input="plain text content")))

    assert result.status == "success"
    assert result.summary == "plain text answer"
    assert result.output == {"raw_text": "plain text answer"}


def test_agent_runtime_should_report_tool_records_as_current_run_count() -> None:
    model_runtime = ReusableToolCallingModelRuntime()
    tool_runtime = ToolRuntime()
    tool_runtime.register_tool(
        ToolSpec(
            name="calculator",
            args_schema={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        ),
        lambda args: {"result": 3 if str(args["expression"]).replace(" ", "") == "1+2" else 0},
    )
    runtime = AgentRuntime(model_runtime=model_runtime, tool_runtime=tool_runtime)

    first = asyncio.run(runtime.arun(AgentRunRequest(task_input="calculate first")))
    second = asyncio.run(runtime.arun(AgentRunRequest(task_input="calculate second")))

    assert first.status == "success"
    assert second.status == "success"
    assert first.metadata["tool_records"] == 1
    assert second.metadata["tool_records"] == 1


def test_agent_runtime_should_keep_tool_record_count_isolated_per_concurrent_run() -> None:
    model_runtime = PhaseAwareToolCallingModelRuntime()
    tool_runtime = ToolRuntime()

    async def _calculator(args: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.01)
        return {"result": 3 if str(args["expression"]).replace(" ", "") == "1+2" else 0}

    tool_runtime.register_tool(
        ToolSpec(
            name="calculator",
            args_schema={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        ),
        _calculator,
    )
    runtime = AgentRuntime(model_runtime=model_runtime, tool_runtime=tool_runtime)

    async def _run_pair() -> tuple[Any, Any]:
        return await asyncio.gather(
            runtime.arun(AgentRunRequest(task_input="calculate first")),
            runtime.arun(AgentRunRequest(task_input="calculate second")),
        )

    first, second = asyncio.run(_run_pair())

    assert first.status == "success"
    assert second.status == "success"
    assert first.metadata["tool_records"] == 1
    assert second.metadata["tool_records"] == 1


def test_agent_runtime_should_namespace_tool_call_ids_per_run() -> None:
    model_runtime = ReusableToolCallingModelRuntime()
    tool_runtime = ToolRuntime()
    tool_runtime.register_tool(
        ToolSpec(
            name="calculator",
            args_schema={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        ),
        lambda args: {"result": 3 if str(args["expression"]).replace(" ", "") == "1+2" else 0},
    )
    runtime = AgentRuntime(model_runtime=model_runtime, tool_runtime=tool_runtime)

    first = asyncio.run(runtime.arun(AgentRunRequest(task_input="calculate first")))
    second = asyncio.run(runtime.arun(AgentRunRequest(task_input="calculate second")))
    records = tool_runtime.get_records()

    assert first.status == "success"
    assert second.status == "success"
    assert len(records) == 2
    assert records[0].tool_call_id != records[1].tool_call_id
    assert ":tc_calc_" in records[0].tool_call_id
    assert ":tc_calc_" in records[1].tool_call_id


def test_agent_runtime_should_use_memory_write_counters_when_records_are_empty() -> None:
    model_runtime = ToolCallingModelRuntime()
    tool_runtime = ToolRuntime()
    tool_runtime.register_tool(
        ToolSpec(
            name="calculator",
            args_schema={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        ),
        lambda args: {"result": 3 if str(args["expression"]).replace(" ", "") == "1+2" else 0},
    )
    runtime = AgentRuntime(
        model_runtime=model_runtime,
        tool_runtime=tool_runtime,
        memory_runtime=CountingMemoryRuntime(),
    )

    result = asyncio.run(
        runtime.arun(
            AgentRunRequest(
                task_input="calculate with memory",
                tenant_id="tenant_a",
                user_id="user_a",
            )
        )
    )

    assert result.status == "success"
    assert result.metadata["memory_write_count"] == 4


def test_agent_runtime_should_not_write_memory_for_failed_final_answer() -> None:
    memory_runtime = RecordingMemoryRuntime()
    runtime = AgentRuntime(
        model_runtime=ToolCallingModelRuntime(),
        tool_runtime=ToolRuntime(),
        memory_runtime=memory_runtime,
    )

    result = asyncio.run(
        runtime.arun(
            AgentRunRequest(
                task_input="calculate failure",
                tenant_id="tenant_a",
                user_id="user_a",
            )
        )
    )

    assert result.status == "failed"
    assert result.metadata["memory_write_count"] == 0
    assert memory_runtime.write_requests == []


def test_agent_runtime_should_only_write_fact_memory_for_successful_tool_results() -> None:
    model_runtime = ToolCallingModelRuntime()
    tool_runtime = ToolRuntime()
    tool_runtime.register_tool(
        ToolSpec(
            name="calculator",
            args_schema={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        ),
        lambda args: {"result": 3 if str(args["expression"]).replace(" ", "") == "1+2" else 0},
    )
    memory_runtime = RecordingMemoryRuntime()
    runtime = AgentRuntime(
        model_runtime=model_runtime,
        tool_runtime=tool_runtime,
        memory_runtime=memory_runtime,
    )

    result = asyncio.run(
        runtime.arun(
            AgentRunRequest(
                task_input="calculate success",
                tenant_id="tenant_a",
                user_id="user_a",
            )
        )
    )

    assert result.status == "success"
    assert [item.trigger for item in memory_runtime.write_requests] == ["finish", "fact"]
    assert len(memory_runtime.write_requests[1].tool_results) == 1
    assert memory_runtime.write_requests[1].tool_results[0].status == "ok"


def test_agent_should_return_structured_error_from_on_error() -> None:
    class ErrorAgentRuntime(AgentRuntime):
        async def arun(self, request: AgentRunRequest):  # type: ignore[override]
            raise RuntimeError(f"boom:{request.task_input}")

    from agent_forge import Agent

    result = asyncio.run(Agent(runtime=ErrorAgentRuntime()).arun("explode"))

    assert result.status == "failed"
    assert result.error == ErrorInfo(
        error_code="AGENT_RUNTIME_EXCEPTION",
        error_message="boom:explode",
        retryable=False,
    )
