"""Agent 入口层的公共配置与请求/响应模型。"""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from agent_forge.components.protocol import ErrorInfo, FinalAnswer


class AgentConfig(BaseModel):
    """定义 `Agent` 与 `AgentRuntime` 的默认运行配置。"""

    config_version: str = Field(default="v1", min_length=1, description="配置版本号。")
    default_principal: str = Field(default="agent", min_length=1, description="默认执行主体。")
    session_id_prefix: str = Field(default="session", min_length=1, description="自动生成 session_id 时使用的前缀。")
    default_model: str = Field(default="agent-default-stub", min_length=1, description="默认模型名。")
    tool_version: str = Field(default="tool-runtime-v1", min_length=1, description="工具运行时版本。")
    policy_version: str = Field(default="v1", min_length=1, description="安全策略版本。")
    enable_evaluator_by_default: bool = Field(default=False, description="是否默认开启评测。")


class AgentRunRequest(BaseModel):
    """统一封装一次 Agent 运行所需的输入。"""

    task_input: str = Field(..., min_length=1, description="用户任务输入。")
    session_id: str | None = Field(default=None, description="会话 ID；为空时由运行时自动生成。")
    trace_id: str | None = Field(default=None, description="链路追踪 ID。")
    principal: str | None = Field(default=None, description="本次运行的主体标识。")
    capabilities: set[str] | None = Field(default=None, description="本次运行允许的能力集合。")
    context: dict[str, Any] = Field(default_factory=dict, description="额外上下文字段。")
    tenant_id: str | None = Field(default=None, description="租户 ID。")
    user_id: str | None = Field(default=None, description="用户 ID。")
    evaluate: bool | None = Field(default=None, description="是否开启评测。")
    metadata: dict[str, Any] = Field(default_factory=dict, description="附加元数据。")


class AgentResult(BaseModel):
    """定义 `Agent` 对外返回的稳定结果结构。"""

    status: Literal["success", "partial", "failed", "blocked"] = Field(..., description="本次运行状态。")
    summary: str = Field(..., min_length=1, description="面向调用方的摘要。")
    output: dict[str, Any] = Field(default_factory=dict, description="结构化输出载荷。")
    session_id: str = Field(..., min_length=1, description="本次运行所属的 session_id。")
    trace_id: str = Field(..., min_length=1, description="本次运行的 trace_id。")
    references: list[str] = Field(default_factory=list, description="引用来源。")
    safety: dict[str, Any] = Field(default_factory=dict, description="输入/输出安全审查摘要。")
    error: ErrorInfo | None = Field(default=None, description="失败时的结构化错误。")
    final_answer: FinalAnswer | None = Field(default=None, description="原始 FinalAnswer。")
    evaluation: dict[str, Any] | None = Field(default=None, description="可选评测结果。")
    metadata: dict[str, Any] = Field(default_factory=dict, description="运行附加统计。")


def build_generated_session_id(prefix: str) -> str:
    """生成统一格式的 session_id。"""

    return f"{prefix}_{uuid4().hex}"
