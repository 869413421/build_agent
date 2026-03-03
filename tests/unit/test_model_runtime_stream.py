"""Model Runtime stream tests."""

from __future__ import annotations

from collections.abc import Iterator

from agent_forge.components.model_runtime import (
    ModelRequest,
    ModelResponse,
    ModelRuntime,
    ModelStats,
    ModelStreamEvent,
    ProviderAdapter,
    StubOpenAIAdapter,
)
from agent_forge.components.protocol import AgentMessage, ErrorInfo


class _RecordingHooks:
    def __init__(self) -> None:
        self.before_called = False
        self.after_called = False
        self.event_count = 0

    def before_request(self, request: ModelRequest) -> ModelRequest:
        self.before_called = True
        return request

    def on_stream_event(self, event: ModelStreamEvent) -> ModelStreamEvent:
        self.event_count += 1
        event.metadata["hooked"] = True
        return event

    def after_response(self, response: ModelResponse) -> ModelResponse:
        self.after_called = True
        return response


class _ErrorStreamAdapter(ProviderAdapter):
    def generate(self, request: ModelRequest, **kwargs: object) -> ModelResponse:
        return ModelResponse(content="")

    def generate_stream(self, request: ModelRequest, **kwargs: object) -> Iterator[ModelStreamEvent]:
        req_id = request.request_id or "req_error"
        yield ModelStreamEvent(event_type="start", request_id=req_id, sequence=0, timestamp_ms=1)
        yield ModelStreamEvent(
            event_type="error",
            request_id=req_id,
            sequence=1,
            timestamp_ms=2,
            error=ErrorInfo(error_code="MODEL_TIMEOUT", error_message="timeout", retryable=True),
        )
        yield ModelStreamEvent(
            event_type="end",
            request_id=req_id,
            sequence=2,
            timestamp_ms=3,
            metadata={"status": "error"},
        )


class _ClosableIterator:
    def __init__(self) -> None:
        self.closed = False
        self._idx = 0
        self._events = [
            ModelStreamEvent(event_type="start", request_id="req_close", sequence=0, timestamp_ms=1),
            ModelStreamEvent(event_type="delta", request_id="req_close", sequence=1, timestamp_ms=2, delta="hello"),
            ModelStreamEvent(event_type="end", request_id="req_close", sequence=2, timestamp_ms=3, content="hello"),
        ]

    def __iter__(self) -> "_ClosableIterator":
        return self

    def __next__(self) -> ModelStreamEvent:
        if self._idx >= len(self._events):
            raise StopIteration
        item = self._events[self._idx]
        self._idx += 1
        return item

    def close(self) -> None:
        self.closed = True


class _ClosableAdapter(ProviderAdapter):
    def __init__(self) -> None:
        self.iterator = _ClosableIterator()

    def generate(self, request: ModelRequest, **kwargs: object) -> ModelResponse:
        return ModelResponse(content="")

    def generate_stream(self, request: ModelRequest, **kwargs: object) -> Iterator[ModelStreamEvent]:
        return self.iterator


def test_stream_generate_happy_path_with_hooks() -> None:
    req = ModelRequest(messages=[AgentMessage(role="user", content="hello")], request_id="req_stream")
    runtime = ModelRuntime(adapter=StubOpenAIAdapter(mock_response='{"answer":"ok"}'))
    hooks = _RecordingHooks()

    events = list(runtime.stream_generate(req, hooks=hooks))
    types = [e.event_type for e in events]

    assert types[0] == "start"
    assert "delta" in types
    assert types[-1] == "end"
    assert all(e.request_id == "req_stream" for e in events)
    assert all(e.metadata.get("hooked") is True for e in events)
    assert hooks.before_called is True
    assert hooks.after_called is True
    assert runtime.last_stream_response is not None
    assert runtime.last_stream_response.content == '{"answer":"ok"}'


def test_stream_generate_error_boundary() -> None:
    req = ModelRequest(messages=[AgentMessage(role="user", content="hello")], request_id="req_error")
    runtime = ModelRuntime(adapter=_ErrorStreamAdapter())

    events = list(runtime.stream_generate(req))
    assert [e.event_type for e in events] == ["start", "error", "end"]
    assert events[1].error is not None
    assert events[1].error.error_code == "MODEL_TIMEOUT"
    assert events[-1].metadata["status"] == "error"


def test_stream_generate_close_on_consumer_interrupt() -> None:
    req = ModelRequest(messages=[AgentMessage(role="user", content="hello")], request_id="req_close")
    adapter = _ClosableAdapter()
    runtime = ModelRuntime(adapter=adapter)

    iterator = runtime.stream_generate(req)
    first = next(iterator)
    assert first.event_type == "start"
    iterator.close()

    assert adapter.iterator.closed is True


def test_stream_generate_parsed_output_on_end() -> None:
    req = ModelRequest(
        messages=[AgentMessage(role="user", content="hello")],
        request_id="req_schema",
        response_schema={"required": ["answer"]},
    )
    runtime = ModelRuntime(adapter=StubOpenAIAdapter(mock_response='{"answer":"ok"}'))
    _ = list(runtime.stream_generate(req))

    assert runtime.last_stream_response is not None
    assert runtime.last_stream_response.parsed_output == {"answer": "ok"}
    assert isinstance(runtime.last_stream_response.stats, ModelStats)
