"""Protocol 组件测试。"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from labor_agent.core.protocol import (
    PROTOCOL_VERSION,
    AgentMessage,
    AgentState,
    ErrorInfo,
    ExecutionEvent,
    FinalAnswer,
    ToolCall,
    ToolResult,
    build_initial_state,
)


def test_initial_state_contains_required_ids_and_version() -> None:
    """初始状态应自动带 trace/run/protocol 字段。"""

    state = build_initial_state("session_001")
    assert state.session_id == "session_001"
    assert state.trace_id.startswith("trace_")
    assert state.run_id.startswith("run_")
    assert state.protocol_version == PROTOCOL_VERSION


def test_protocol_roundtrip_json_serialization() -> None:
    """协议对象应支持 JSON 序列化与反序列化。"""

    message = AgentMessage(role="user", content="公司拖欠工资")
    call = ToolCall(
        tool_call_id="tc_001",
        tool_name="labor_law_search",
        args={"query": "拖欠工资"},
        principal="worker_user",
    )
    result = ToolResult(tool_call_id="tc_001", status="ok", output={"hits": 2}, latency_ms=18)
    event = ExecutionEvent(
        trace_id="trace_001",
        run_id="run_001",
        step_id="step_001",
        event_type="tool_result",
        payload={"tool_call_id": "tc_001"},
    )
    final = FinalAnswer(
        status="success",
        summary="任务已完成并生成结构化结果",
        output={"answer": "工资争议处理建议", "priority": "high"},
        artifacts=[{"type": "plan", "id": "plan_001"}],
        references=["labor_law_search:doc_123"],
    )
    state = AgentState(
        session_id="session_002",
        messages=[message],
        tool_calls=[call],
        tool_results=[result],
        events=[event],
        final_answer=final,
    )

    raw = state.model_dump_json(ensure_ascii=False)
    data = json.loads(raw)
    loaded = AgentState.model_validate(data)
    assert loaded.session_id == "session_002"
    assert loaded.tool_calls[0].tool_name == "labor_law_search"
    assert loaded.final_answer is not None
    assert loaded.final_answer.protocol_version == PROTOCOL_VERSION
    assert loaded.final_answer.status == "success"


def test_blank_fields_must_fail_validation() -> None:
    """空白关键字段必须校验失败。"""

    with pytest.raises(ValidationError):
        ToolCall(tool_call_id=" ", tool_name="t", args={}, principal="p")

    with pytest.raises(ValidationError):
        AgentState(session_id="   ")


def test_error_info_schema() -> None:
    """错误结构应稳定且带协议版本。"""

    err = ErrorInfo(error_code="TOOL_TIMEOUT", error_message="tool timeout", retryable=True)
    assert err.retryable is True
    assert err.protocol_version == PROTOCOL_VERSION
