"""Model Runtime 组件测试。"""

from __future__ import annotations

import time
from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from agent_forge.components.model_runtime import (
    DeepSeekAdapter,
    ModelRequest,
    ModelResponse,
    ModelRuntime,
    ModelStats,
    OpenAIAdapter,
    ProviderAdapter,
    StubDeepSeekAdapter,
    StubOpenAIAdapter,
)
from agent_forge.components.model_runtime.domain.schemas import ModelParseError, ModelStreamEvent
from agent_forge.components.protocol import AgentMessage


class _BrokenJSONAdapter(ProviderAdapter):
    """会固定输出破损 JSON 的测试适配器，用于验证自愈流程。"""

    def __init__(self, failure_count: int = 1):
        self.failure_count = failure_count
        self.call_count = 0

    def generate(self, request: ModelRequest, **kwargs: object) -> ModelResponse:
        self.call_count += 1
        
        # 前 N 次返回破损 JSON
        if self.call_count <= self.failure_count:
            content = '```json\n{"status": "ok", "missing_key": true\n```'
        else:
            # 之后返回正确格式
            content = '{"status": "ok", "required_key": "fixed_value"}'

        return ModelResponse(
            content=content,
            stats=ModelStats(
                prompt_tokens=10 * self.call_count,
                completion_tokens=5,
                total_tokens=10 * self.call_count + 5,
                latency_ms=100,
                cost_usd=0.001,
            ),
        )

    def generate_stream(self, request: ModelRequest, **kwargs: object) -> Iterator[ModelStreamEvent]:
        now = int(time.time() * 1000)
        yield ModelStreamEvent(event_type="start", request_id=request.request_id or "req_test", sequence=0, timestamp_ms=now)
        yield ModelStreamEvent(event_type="delta", request_id=request.request_id or "req_test", sequence=1, delta="{", timestamp_ms=now)
        yield ModelStreamEvent(event_type="end", request_id=request.request_id or "req_test", sequence=2, content="{", timestamp_ms=now)


class _CaptureRequestAdapter(ProviderAdapter):
    """捕获请求以验证 generate hooks 行为。"""

    def __init__(self) -> None:
        self.captured_request: ModelRequest | None = None

    def generate(self, request: ModelRequest, **kwargs: object) -> ModelResponse:
        self.captured_request = request
        return ModelResponse(content='{"ok": true}', stats=ModelStats(total_tokens=1))

    def generate_stream(self, request: ModelRequest, **kwargs: object) -> Iterator[ModelStreamEvent]:
        now = int(time.time() * 1000)
        yield ModelStreamEvent(event_type="start", request_id=request.request_id or "req_capture", sequence=0, timestamp_ms=now)
        yield ModelStreamEvent(event_type="end", request_id=request.request_id or "req_capture", sequence=1, content='{"ok": true}', timestamp_ms=now)


class _GenerateHooks:
    def __init__(self) -> None:
        self.before_called = False
        self.after_called = False

    def before_request(self, request: ModelRequest) -> ModelRequest:
        self.before_called = True
        request.messages.append(AgentMessage(role="system", content="hook_injected"))
        return request

    def on_stream_event(self, event: ModelStreamEvent) -> ModelStreamEvent:
        return event

    def after_response(self, response: ModelResponse) -> ModelResponse:
        self.after_called = True
        return response


class _FakeCompletions:
    def __init__(self, response: object):
        self.response = response
        self.last_kwargs: dict | None = None

    def create(self, **kwargs: dict) -> object:
        self.last_kwargs = kwargs
        return self.response


def _build_fake_client(content: str = '{"answer":"ok"}') -> tuple[object, _FakeCompletions]:
    usage = SimpleNamespace(prompt_tokens=11, completion_tokens=7, total_tokens=18)
    message = SimpleNamespace(content=content, tool_calls=[])
    choice = SimpleNamespace(message=message)
    response = SimpleNamespace(choices=[choice], usage=usage)
    completions = _FakeCompletions(response=response)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return client, completions


def test_provider_stub_switching_and_telemetry() -> None:
    """验证模型提供商可切换，且 telemetry 数据被正确映射。"""
    
    req = ModelRequest(messages=[AgentMessage(role="user", content="hello")])
    
    # 测试 OpenAI Stub
    openai_adapter = StubOpenAIAdapter(mock_response='{"answer": "openai"}')
    runtime_openai = ModelRuntime(adapter=openai_adapter)
    res_open = runtime_openai.generate(req)
    
    assert "openai" in res_open.content
    assert res_open.stats.total_tokens == 150
    assert res_open.stats.latency_ms == 150

    # 测试 DeepSeek Stub
    deepseek_adapter = StubDeepSeekAdapter(mock_response='{"answer": "deepseek"}')
    runtime_deepseek = ModelRuntime(adapter=deepseek_adapter)
    res_deep = runtime_deepseek.generate(req)
    
    assert "deepseek" in res_deep.content
    assert res_deep.stats.total_tokens == 120
    assert res_deep.stats.latency_ms == 120


def test_openai_adapter_should_pass_extended_params() -> None:
    """验证 OpenAIAdapter 透传扩展参数。"""

    client, completions = _build_fake_client('{"answer":"openai"}')
    adapter = OpenAIAdapter(api_key="test-key", model="gpt-4o-mini", client=client)
    runtime = ModelRuntime(adapter=adapter)
    req = ModelRequest(
        messages=[AgentMessage(role="user", content="hello")],
        top_p=0.9,
        frequency_penalty=0.1,
        presence_penalty=0.2,
        seed=42,
        n=1,
        stop=["END"],
        timeout_ms=5000,
        user="u-1",
        metadata={"scene": "unit-test"},
        reasoning_effort="medium",
        top_logprobs=3,
    )

    res = runtime.generate(req)
    kwargs = completions.last_kwargs or {}

    assert res.content == '{"answer":"openai"}'
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["top_p"] == 0.9
    assert kwargs["frequency_penalty"] == 0.1
    assert kwargs["presence_penalty"] == 0.2
    assert kwargs["seed"] == 42
    assert kwargs["stop"] == ["END"]
    assert kwargs["timeout"] == 5
    assert kwargs["user"] == "u-1"
    assert kwargs["metadata"]["scene"] == "unit-test"
    assert kwargs["reasoning_effort"] == "medium"
    assert kwargs["top_logprobs"] == 3


def test_runtime_level_kwargs_should_override_request_kwargs() -> None:
    """验证 Runtime.generate(**kwargs) 可覆盖请求透传参数。"""

    client, completions = _build_fake_client('{"answer":"openai"}')
    adapter = OpenAIAdapter(api_key="test-key", model="gpt-4o-mini", client=client)
    runtime = ModelRuntime(adapter=adapter)
    req = ModelRequest(
        messages=[AgentMessage(role="user", content="hello")],
        reasoning_effort="low",
    )

    runtime.generate(req, reasoning_effort="high")
    kwargs = completions.last_kwargs or {}
    assert kwargs["reasoning_effort"] == "high"


def test_adapter_should_not_forward_internal_context_extras() -> None:
    """验证内部上下文字段不会透传到厂商 API 载荷。"""

    client, completions = _build_fake_client('{"answer":"openai"}')
    adapter = OpenAIAdapter(api_key="test-key", model="gpt-4o-mini", client=client)
    runtime = ModelRuntime(adapter=adapter)
    req = ModelRequest(
        messages=[AgentMessage(role="user", content="hello")],
        context_budget_report={"available_tokens": 100},
        citations=[{"title": "Doc 1"}],
    )

    runtime.generate(req)
    kwargs = completions.last_kwargs or {}

    assert "context_budget_report" not in kwargs
    assert "citations" not in kwargs


def test_deepseek_adapter_should_use_provider_defaults() -> None:
    """验证 DeepSeekAdapter 默认模型和统计字段可用。"""

    client, completions = _build_fake_client('{"answer":"deepseek"}')
    adapter = DeepSeekAdapter(api_key="test-key", model="deepseek-chat", client=client)
    runtime = ModelRuntime(adapter=adapter)
    req = ModelRequest(messages=[AgentMessage(role="user", content="hello deepseek")])

    res = runtime.generate(req)
    kwargs = completions.last_kwargs or {}

    assert kwargs["model"] == "deepseek-chat"
    assert "deepseek" in res.content
    assert res.stats.total_tokens == 18


def test_response_format_json_object_should_pass_through() -> None:
    """验证 response_format 可作为通用参数透传。"""

    client, completions = _build_fake_client('{"answer":"deepseek","confidence":0.9}')
    adapter = DeepSeekAdapter(api_key="test-key", model="deepseek-chat", client=client)
    runtime = ModelRuntime(adapter=adapter)
    req = ModelRequest(
        messages=[AgentMessage(role="user", content="hello deepseek")],
        response_schema={"type": "object", "required": ["answer", "confidence"]},
    )

    runtime.generate(req, response_format={"type": "json_object"})
    kwargs = completions.last_kwargs or {}
    assert kwargs["response_format"]["type"] == "json_object"
    assert any("JSON Schema" in (m.get("content", "")) for m in kwargs["messages"])


def test_structural_output_validation() -> None:
    """验证 JSON Schema 结构解析是否正常工作。"""
    
    req = ModelRequest(
        messages=[AgentMessage(role="user", content="hello")],
        response_schema={"required": ["answer", "confidence"]}
    )
    
    # 提供满足 schema 的 stub
    adapter = StubOpenAIAdapter(mock_response='{"answer": "yes", "confidence": 0.99}')
    runtime = ModelRuntime(adapter=adapter)
    res = runtime.generate(req)
    
    assert res.parsed_output is not None
    assert res.parsed_output["answer"] == "yes"
    assert res.parsed_output["confidence"] == 0.99


def test_self_healing_retry_flow_success() -> None:
    """验证在遇到非法 JSON 时，系统会自动重试并成功自愈。"""
    
    req = ModelRequest(
        messages=[AgentMessage(role="user", content="hello")],
        response_schema={"required": ["required_key"]}
    )
    
    adapter = _BrokenJSONAdapter(failure_count=1)
    runtime = ModelRuntime(adapter=adapter, max_retries=2)
    
    # 第一次会失败，触发重试，第二次返回正确的格式
    res = runtime.generate(req)
    
    assert adapter.call_count == 2
    assert res.parsed_output is not None
    assert res.parsed_output["required_key"] == "fixed_value"
    
    # 验证修复请求是否被加到上下文里
    # 注意：在 adapter 内查看不好查，但在 runtime 层 逻辑上是正确的
    # 此处依赖于 adapter.call_count 确保发送了额外的请求


def test_self_healing_retry_flow_exceeds_limit() -> None:
    """验证超过重试次数依然失败的场景。"""
    
    req = ModelRequest(
        messages=[AgentMessage(role="user", content="hello")],
        response_schema={"required": ["required_key"]}
    )
    
    # 强制让它失败 5 次，但最大重试只允许 2 次
    adapter = _BrokenJSONAdapter(failure_count=5)
    runtime = ModelRuntime(adapter=adapter, max_retries=2)
    
    with pytest.raises(ModelParseError) as exc_info:
        runtime.generate(req)
        
    assert "JSON 格式非法" in str(exc_info.value.message)
    # 因为首调用 + 2次重试 = 3次
    assert adapter.call_count == 3


def test_generate_should_call_hooks_for_non_stream() -> None:
    req = ModelRequest(messages=[AgentMessage(role="user", content="hello")])
    hooks = _GenerateHooks()
    adapter = _CaptureRequestAdapter()
    runtime = ModelRuntime(adapter=adapter)

    response = runtime.generate(req, hooks=hooks)

    assert response.content == '{"ok": true}'
    assert hooks.before_called is True
    assert hooks.after_called is True
    assert adapter.captured_request is not None
    assert adapter.captured_request.messages[-1].content == "hook_injected"


