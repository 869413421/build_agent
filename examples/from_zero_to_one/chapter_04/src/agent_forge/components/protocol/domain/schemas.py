"""Protocol 组件（框架契约层）。

为什么单独做这一层：
1. 让 Engine、Model Runtime、Tool Runtime 共享同一套数据契约。
2. 给 Observability/Evaluator 提供稳定的结构化输入。
3. 通过版本字段控制协议演进，避免“改一个字段全链路崩”。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

PROTOCOL_VERSION = "v1"


def _now_iso() -> str:
    """统一事件时间格式。

    使用 UTC ISO 字符串，便于日志系统、数据仓库和跨时区排查统一处理。
    """

    return datetime.now(timezone.utc).isoformat()


class ErrorInfo(BaseModel):
    """统一错误结构。

    约束：
    - 所有运行时错误最终都应映射到这里。
    - `retryable` 由 Runtime 层给出，用于指导 Engine 的重试决策。
    """

    error_code: str = Field(..., min_length=1, description="错误码")
    error_message: str = Field(..., min_length=1, description="错误信息")
    retryable: bool = Field(default=False, description="是否可重试")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class AgentMessage(BaseModel):
    """智能体消息对象。

    说明：
    - `role` 用 Literal 固定取值，防止上游传入未知角色破坏上下文拼装。
    - `message_id` 自动生成，确保每条消息都可在 trace 中被唯一定位。
    """

    message_id: str = Field(default_factory=lambda: f"msg_{uuid4().hex}", description="消息 ID")
    role: Literal["system", "developer", "user", "assistant", "tool"] = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, description="消息内容")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    created_at: str = Field(default_factory=_now_iso, description="创建时间")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class ToolCall(BaseModel):
    """工具调用请求。

    说明：
    - `tool_call_id` 是幂等键；重试时可据此避免重复副作用执行。
    - `principal` 预留给权限系统，后续可接入 capability 校验。
    """

    tool_call_id: str = Field(..., min_length=1, description="工具调用唯一 ID")
    tool_name: str = Field(..., min_length=1, description="工具名称")
    args: dict[str, Any] = Field(default_factory=dict, description="工具参数")
    principal: str = Field(..., min_length=1, description="调用主体，用于权限控制")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")

    @field_validator("tool_call_id", "tool_name", "principal")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        # 防止“看起来有值、实际上是空白”的脏数据流入执行链路。
        if not value.strip():
            raise ValueError("字段不能为空白字符")
        return value


class ToolResult(BaseModel):
    """工具调用结果。

    说明：
    - `status` 明确区分成功/失败，避免通过是否有异常字段来“猜状态”。
    - `latency_ms` 是后续可观测性最小指标字段。
    """

    tool_call_id: str = Field(..., min_length=1, description="对应的调用 ID")
    status: Literal["ok", "error"] = Field(..., description="执行状态")
    output: dict[str, Any] = Field(default_factory=dict, description="输出内容")
    error: ErrorInfo | None = Field(default=None, description="错误信息")
    latency_ms: int = Field(default=0, ge=0, description="耗时毫秒")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class ExecutionEvent(BaseModel):
    """执行事件（用于 trace、回放、评测）。

    字段语义：
    - `trace_id`：一次链路的全局 ID。
    - `run_id`：同一 trace 下某次运行实例。
    - `step_id`：运行实例中的步骤定位点。
    """

    trace_id: str = Field(..., min_length=1, description="链路 ID")
    run_id: str = Field(..., min_length=1, description="运行 ID")
    step_id: str = Field(..., min_length=1, description="步骤 ID")
    parent_step_id: str | None = Field(default=None, description="父步骤 ID")
    event_type: Literal["plan", "tool_call", "tool_result", "state_update", "finish", "error"] = Field(
        ..., description="事件类型"
    )
    payload: dict[str, Any] = Field(default_factory=dict, description="事件数据")
    error: ErrorInfo | None = Field(default=None, description="事件错误")
    created_at: str = Field(default_factory=_now_iso, description="创建时间")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class FinalAnswer(BaseModel):
    """结构化最终输出。

    设计目的：
    - 保持领域无关，适用于任意 Agent 任务结果。
    - 让前端展示、评测打分、审计留痕可以直接消费固定字段。
    """

    status: Literal["success", "partial", "failed"] = Field(..., description="任务完成状态")
    summary: str = Field(..., min_length=1, description="结果摘要")
    output: dict[str, Any] = Field(default_factory=dict, description="结构化结果内容")
    artifacts: list[dict[str, Any]] = Field(default_factory=list, description="执行产物清单")
    references: list[str] = Field(default_factory=list, description="可选参考信息")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class AgentState(BaseModel):
    """运行状态对象（Engine 的单一事实源）。

    约束：
    - Engine 只读写这个状态对象，不在外部散落临时状态。
    - 未来 snapshot/restore 将基于该对象序列化实现。
    """

    session_id: str = Field(..., min_length=1, description="会话 ID")
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid4().hex}", description="链路 ID")
    run_id: str = Field(default_factory=lambda: f"run_{uuid4().hex}", description="运行 ID")
    messages: list[AgentMessage] = Field(default_factory=list, description="消息列表")
    tool_calls: list[ToolCall] = Field(default_factory=list, description="工具调用记录")
    tool_results: list[ToolResult] = Field(default_factory=list, description="工具结果记录")
    events: list[ExecutionEvent] = Field(default_factory=list, description="执行事件记录")
    final_answer: FinalAnswer | None = Field(default=None, description="最终结构化输出")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")

    @field_validator("session_id")
    @classmethod
    def _session_id_not_blank(cls, value: str) -> str:
        # session_id 是状态分区键，禁止空白可避免跨会话数据污染。
        if not value.strip():
            raise ValueError("session_id 不能为空白字符")
        return value


def build_initial_state(session_id: str) -> AgentState:
    """创建初始状态。

    这是 Engine loop 的标准起点，后续章节统一从这里进入执行流程。
    """

    return AgentState(session_id=session_id)

