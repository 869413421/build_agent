"""Tool Runtime 组件领域模型。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from agent_forge.components.protocol import ErrorInfo, ToolCall, ToolResult, PROTOCOL_VERSION


def _now_iso() -> str:
    """统一记录时间格式。"""

    return datetime.now(timezone.utc).isoformat()


class ToolSpec(BaseModel):
    """工具规格定义。"""

    name: str = Field(..., min_length=1, description="工具名称")
    description: str = Field(default="", description="工具说明")
    args_schema: dict[str, Any] = Field(default_factory=dict, description="JSON Schema 风格参数定义")
    required_capabilities: set[str] = Field(default_factory=set, description="执行该工具所需能力集")
    sensitive_fields: set[str] = Field(default_factory=set, description="需要在记录中脱敏的参数字段")
    timeout_ms: int | None = Field(default=None, ge=1, description="工具级超时")
    side_effect_level: Literal["none", "low", "high"] = Field(default="none", description="副作用等级")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class ToolExecutionRecord(BaseModel):
    """工具执行记录（用于回放与审计）。"""

    tool_call_id: str = Field(..., min_length=1, description="工具调用ID")
    tool_name: str = Field(..., min_length=1, description="工具名称")
    principal: str = Field(..., min_length=1, description="执行主体")
    status: Literal["ok", "error"] = Field(..., description="执行状态")
    args_masked: dict[str, Any] = Field(default_factory=dict, description="脱敏后的参数")
    output: dict[str, Any] = Field(default_factory=dict, description="输出")
    error: ErrorInfo | None = Field(default=None, description="错误")
    latency_ms: int = Field(default=0, ge=0, description="耗时")
    created_at: str = Field(default_factory=_now_iso, description="记录时间")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class ToolRuntimeError(Exception):
    """Tool Runtime 内部统一异常。"""

    def __init__(self, error_code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.retryable = retryable


class ToolRuntimeEvent(BaseModel):
    """工具运行时事件（用于 hooks 与观测）。"""

    event_type: Literal[
        "before_execute",
        "after_execute",
        "error",
        "cache_hit",
        "chain_step_start",
        "chain_step_end",
    ] = Field(..., description="事件类型")
    tool_call_id: str = Field(default="", description="调用ID")
    tool_name: str = Field(default="", description="工具名")
    chain_id: str | None = Field(default=None, description="链路ID")
    step_id: str | None = Field(default=None, description="链路步骤ID")
    attempt: int = Field(default=0, ge=0, description="尝试次数")
    latency_ms: int | None = Field(default=None, ge=0, description="耗时")
    payload: dict[str, Any] = Field(default_factory=dict, description="扩展信息")
    error: ErrorInfo | None = Field(default=None, description="错误信息")
    created_at: str = Field(default_factory=_now_iso, description="创建时间")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class ToolRuntimeHooks(Protocol):
    """工具运行时 hooks 协议。"""

    def before_execute(self, tool_call: ToolCall) -> ToolCall:
        """工具执行前钩子。"""

    def on_event(self, event: ToolRuntimeEvent) -> ToolRuntimeEvent | None:
        """事件钩子。"""

    def after_execute(self, result: ToolResult) -> ToolResult:
        """工具执行后钩子。"""

    def on_error(self, error: ToolRuntimeError, tool_call: ToolCall) -> ToolRuntimeError:
        """错误钩子。"""


class NoopToolRuntimeHooks:
    """默认空 hooks。"""

    def before_execute(self, tool_call: ToolCall) -> ToolCall:
        return tool_call

    def on_event(self, event: ToolRuntimeEvent) -> ToolRuntimeEvent | None:
        return event

    def after_execute(self, result: ToolResult) -> ToolResult:
        return result

    def on_error(self, error: ToolRuntimeError, tool_call: ToolCall) -> ToolRuntimeError:
        return error


class ToolChainStep(BaseModel):
    """工具链步骤。"""

    step_id: str = Field(..., min_length=1, description="步骤ID")
    tool_name: str = Field(..., min_length=1, description="工具名")
    args: dict[str, Any] = Field(default_factory=dict, description="固定参数")
    input_bindings: dict[str, str] = Field(default_factory=dict, description="动态参数绑定 arg -> step.path")
    principal: str | None = Field(default=None, description="步骤执行主体")
    capabilities: set[str] = Field(default_factory=set, description="步骤能力集")
    tool_call_id: str | None = Field(default=None, description="可选调用ID")
    stop_on_error: bool = Field(default=True, description="失败后是否终止链路")
