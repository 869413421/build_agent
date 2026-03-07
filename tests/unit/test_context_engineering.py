"""Context Engineering 组件测试。"""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

from agent_forge.components.context_engineering import (
    CitationItem,
    ContextBudget,
    ContextEngineeringHook,
    ContextEngineeringRuntime,
)
from agent_forge.components.model_runtime import ModelRequest, ModelResponse, ModelRuntime, ModelStats, ProviderAdapter
from agent_forge.components.model_runtime.domain import ModelStreamEvent
from agent_forge.components.protocol import AgentMessage


class _CaptureAdapter(ProviderAdapter):
    """用于断言 Hook 行为的请求捕获适配器。"""

    def __init__(self) -> None:
        self.captured_request: ModelRequest | None = None

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        """捕获请求并返回固定响应。

        Args:
            request: 模型请求。
            **kwargs: 未使用的运行时参数。

        Returns:
            ModelResponse: 固定响应。
        """

        self.captured_request = request
        return ModelResponse(content='{"ok": true}', stats=ModelStats(total_tokens=1))

    def generate_stream(self, request: ModelRequest, **kwargs: Any) -> Iterator[ModelStreamEvent]:
        """返回最小可用的流式响应。

        Args:
            request: 模型请求。
            **kwargs: 未使用的运行时参数。

        Returns:
            Iterator[ModelStreamEvent]: 最小流式事件序列。
        """

        now = int(time.time() * 1000)
        yield ModelStreamEvent(event_type="start", request_id=request.request_id or "req_ctx", sequence=0, timestamp_ms=now)
        yield ModelStreamEvent(
            event_type="end",
            request_id=request.request_id or "req_ctx",
            sequence=1,
            content='{"ok": true}',
            timestamp_ms=now,
        )


def _msg(role: str, content: str) -> AgentMessage:
    """构造协议消息的测试辅助函数。

    Args:
        role: 消息角色。
        content: 消息内容。

    Returns:
        AgentMessage: 构造后的消息对象。
    """

    return AgentMessage(role=role, content=content)


def test_context_engineering_should_keep_all_content_when_budget_is_sufficient() -> None:
    """预算充足时应保留全部消息、工具和引用。"""

    runtime = ContextEngineeringRuntime()
    messages = [
        _msg("user", "hello"),
        _msg("assistant", "world"),
    ]
    tools = [{"type": "function", "function": {"name": "echo", "description": "echo text"}}]
    citations = [
        CitationItem(source_id="doc-1", title="Doc 1", url="https://example.com/1", snippet="snippet"),
    ]
    bundle = runtime.build_bundle(
        system_prompt="You are helpful.",
        messages=messages,
        tools=tools,
        citations=citations,
        budget=ContextBudget(max_input_tokens=500, reserved_output_tokens=32),
    )

    assert len(bundle.messages) == 3
    assert len(bundle.tools) == 1
    assert len(bundle.citations) == 1
    assert bundle.budget_report.dropped_messages == 0
    assert bundle.budget_report.dropped_sections == []
    assert any("回答时请使用以下引用：" in item.content for item in bundle.messages)


def test_context_engineering_should_trim_old_history_when_budget_is_small() -> None:
    """预算不足时应保留近期意图并裁剪旧历史。"""

    runtime = ContextEngineeringRuntime()
    messages = [
        _msg("user", "old-user-" + ("A" * 200)),
        _msg("assistant", "old-assistant-" + ("B" * 200)),
        _msg("user", "latest-user-" + ("C" * 120)),
    ]
    bundle = runtime.build_bundle(
        system_prompt="system",
        messages=messages,
        tools=[],
        citations=[],
        budget=ContextBudget(max_input_tokens=120, reserved_output_tokens=40),
    )

    kept_contents = [item.content for item in bundle.messages]
    assert any("latest-user-" in item for item in kept_contents)
    assert not any("old-user-" in item for item in kept_contents)
    assert bundle.budget_report.dropped_messages >= 1
    assert bundle.budget_report.kept_estimated_tokens <= bundle.budget_report.available_tokens


def test_context_engineering_should_prioritize_tools_over_optional_history() -> None:
    """保守策略下工具应优先于可选历史消息。"""

    runtime = ContextEngineeringRuntime()
    messages = [
        _msg("assistant", "old-history-" + ("X" * 220)),
        _msg("user", "latest-user"),
    ]
    tools = [{"type": "function", "function": {"name": "search", "description": "lookup data"}}]
    bundle = runtime.build_bundle(
        system_prompt="system",
        messages=messages,
        tools=tools,
        citations=[],
        budget=ContextBudget(max_input_tokens=100, reserved_output_tokens=40),
    )

    assert len(bundle.tools) == 1
    assert not any("old-history-" in item.content for item in bundle.messages)


def test_context_engineering_should_report_citation_drop_when_budget_exceeded() -> None:
    """预算报告应记录引用被裁剪。"""

    runtime = ContextEngineeringRuntime()
    citations = [
        CitationItem(
            source_id="doc-1",
            title="Document 1",
            url="https://example.com/doc-1",
            snippet="S" * 300,
        )
    ]
    bundle = runtime.build_bundle(
        system_prompt="system",
        messages=[_msg("user", "latest-user")],
        tools=[],
        citations=citations,
        budget=ContextBudget(max_input_tokens=80, reserved_output_tokens=30),
    )

    assert bundle.budget_report.available_tokens > 0
    assert bundle.budget_report.total_estimated_tokens >= bundle.budget_report.kept_estimated_tokens
    assert "citations_dropped" in bundle.budget_report.dropped_sections


def test_context_engineering_should_materialize_kept_citations_into_messages() -> None:
    """被保留的引用应被注入最终模型消息。"""

    runtime = ContextEngineeringRuntime()
    bundle = runtime.build_bundle(
        system_prompt="system",
        messages=[_msg("user", "latest-user")],
        tools=[],
        citations=[
            CitationItem(
                source_id="doc-1",
                title="Document 1",
                url="https://example.com/doc-1",
                snippet="important fact",
            )
        ],
        budget=ContextBudget(max_input_tokens=300, reserved_output_tokens=40),
    )

    assert len(bundle.citations) == 1
    assert any("回答时请使用以下引用：" in item.content for item in bundle.messages)
    assert any("Document 1" in item.content for item in bundle.messages)


def test_context_engineering_hook_should_integrate_with_model_runtime() -> None:
    """Hook 应在适配器调用前完成请求裁剪。"""

    adapter = _CaptureAdapter()
    runtime = ModelRuntime(adapter=adapter)
    context_runtime = ContextEngineeringRuntime()
    hook = ContextEngineeringHook(
        context_runtime,
        budget=ContextBudget(max_input_tokens=120, reserved_output_tokens=40),
        developer_prompt="必须输出 JSON",
        tools=[{"type": "function", "function": {"name": "echo", "description": "echo"}}],
    )
    request = ModelRequest(
        messages=[
            _msg("assistant", "old-history-" + ("D" * 220)),
            _msg("user", "latest-user"),
        ],
        citations=[
            {
                "source_id": "doc-1",
                "title": "Document 1",
                "url": "https://example.com/doc-1",
                "snippet": "important fact",
            }
        ],
    )

    runtime.generate(request, hooks=hook)
    captured = adapter.captured_request

    assert captured is not None
    assert captured.tools is not None and len(captured.tools) == 1
    assert any(item.role == "developer" for item in captured.messages)
    assert any("Document 1" in item.content for item in captured.messages)
    report = captured.extra_kwargs().get("context_budget_report")
    assert isinstance(report, dict)
    assert "available_tokens" in report


def test_context_engineering_hook_should_preserve_request_tools() -> None:
    """request.tools 应在 Hook 处理后保留。"""

    adapter = _CaptureAdapter()
    runtime = ModelRuntime(adapter=adapter)
    context_runtime = ContextEngineeringRuntime()
    hook = ContextEngineeringHook(
        context_runtime,
        budget=ContextBudget(max_input_tokens=120, reserved_output_tokens=40),
    )
    request = ModelRequest(
        messages=[_msg("user", "latest-user")],
        tools=[{"type": "function", "function": {"name": "request_tool", "description": "from request"}}],
    )

    runtime.generate(request, hooks=hook)
    captured = adapter.captured_request

    assert captured is not None
    assert captured.tools is not None
    assert captured.tools[0]["function"]["name"] == "request_tool"


def test_context_engineering_should_truncate_latest_user_for_tiny_budget() -> None:
    """极小预算下应截断最新用户消息且不超预算。"""

    runtime = ContextEngineeringRuntime()
    bundle = runtime.build_bundle(
        system_prompt="system",
        messages=[_msg("user", "latest-user-" + ("Q" * 600))],
        tools=[],
        citations=[],
        budget=ContextBudget(max_input_tokens=30, reserved_output_tokens=20, min_latest_user_tokens=2),
    )

    assert len(bundle.messages) == 1
    assert bundle.budget_report.truncated_latest_user is True
    assert len(bundle.messages[0].content) < len("latest-user-" + ("Q" * 600))
    assert bundle.budget_report.kept_estimated_tokens <= bundle.budget_report.available_tokens


def test_context_engineering_should_not_drop_mandatory_messages_under_tight_budget() -> None:
    """紧预算下 mandatory 消息应截断而不是丢弃。"""

    runtime = ContextEngineeringRuntime()
    bundle = runtime.build_bundle(
        system_prompt="system",
        messages=[
            _msg("developer", "developer-guidance-" + ("D" * 200)),
            _msg("user", "latest-user-" + ("U" * 200)),
        ],
        tools=[],
        citations=[],
        budget=ContextBudget(max_input_tokens=70, reserved_output_tokens=40),
    )

    roles = [item.role for item in bundle.messages]
    assert "developer" in roles
    assert "user" in roles
    assert bundle.budget_report.kept_estimated_tokens <= bundle.budget_report.available_tokens
