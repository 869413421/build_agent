"""Observability 组件领域模型。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from agent_forge.components.protocol import PROTOCOL_VERSION


def _now_iso() -> str:
    """生成统一 UTC 时间。"""

    return datetime.now(timezone.utc).isoformat()


class SamplingPolicy(BaseModel):
    """采样策略。"""

    success_sample_rate: float = Field(default=0.1, ge=0.0, le=1.0, description="成功事件采样比例")
    keep_error_events: bool = Field(default=True, description="错误事件是否全量保留")


class RedactionPolicy(BaseModel):
    """脱敏策略。"""

    masked_keys: set[str] = Field(
        default_factory=lambda: {"api_key", "token", "password", "secret"},
        description="需要脱敏的字段键名（不区分大小写）",
    )
    mask_text: str = Field(default="***", min_length=1, description="脱敏替换文本")


class TraceRecord(BaseModel):
    """标准化 trace 记录。"""

    trace_id: str = Field(..., min_length=1, description="链路 ID")
    run_id: str = Field(..., min_length=1, description="运行 ID")
    step_id: str = Field(..., min_length=1, description="步骤 ID")
    parent_step_id: str | None = Field(default=None, description="父步骤 ID")
    event_type: str = Field(..., min_length=1, description="事件类型")
    source: Literal["engine", "tool_runtime"] = Field(..., description="事件来源")
    payload: dict[str, Any] = Field(default_factory=dict, description="事件 payload")
    error_code: str | None = Field(default=None, description="错误码")
    error_message: str | None = Field(default=None, description="错误信息")
    latency_ms: int | None = Field(default=None, ge=0, description="延迟毫秒")
    created_at: str = Field(default_factory=_now_iso, description="记录时间")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class MetricPoint(BaseModel):
    """观测指标点。"""

    name: str = Field(..., min_length=1, description="指标名")
    value: float = Field(..., description="指标值")
    labels: dict[str, str] = Field(default_factory=dict, description="指标标签")
    created_at: str = Field(default_factory=_now_iso, description="记录时间")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class ReplayStep(BaseModel):
    """回放步骤快照。"""

    step_id: str = Field(..., min_length=1, description="步骤 ID")
    parent_step_id: str | None = Field(default=None, description="父步骤 ID")
    event_type: str = Field(..., min_length=1, description="事件类型")
    source: str = Field(..., min_length=1, description="事件来源")
    payload: dict[str, Any] = Field(default_factory=dict, description="事件 payload")
    error_code: str | None = Field(default=None, description="错误码")
    created_at: str = Field(default_factory=_now_iso, description="记录时间")


class ReplayBundle(BaseModel):
    """回放聚合结果。"""

    trace_id: str = Field(..., min_length=1, description="链路 ID")
    run_id: str = Field(..., min_length=1, description="运行 ID")
    steps: list[ReplayStep] = Field(default_factory=list, description="步骤结构")
    tool_records: list[dict[str, Any]] = Field(default_factory=list, description="录制工具结果")
    generated_at: str = Field(default_factory=_now_iso, description="生成时间")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class ExportEnvelope(BaseModel):
    """导出数据包。"""

    traces: list[TraceRecord] = Field(default_factory=list, description="trace 记录")
    metrics: list[MetricPoint] = Field(default_factory=list, description="指标记录")
    replay: ReplayBundle | None = Field(default=None, description="回放数据")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")

