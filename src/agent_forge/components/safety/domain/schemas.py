"""Safety 领域模型。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from agent_forge.components.protocol import FinalAnswer, ToolCall


SafetyCheckStage = Literal["input", "tool", "output"]
SafetyAction = Literal["allow", "deny", "downgrade", "handoff"]
SafetySeverity = Literal["low", "medium", "high", "critical"]


def now_iso() -> str:
    """返回统一 UTC 时间字符串。

    Returns:
        str: ISO 格式时间。
    """

    return datetime.now(timezone.utc).isoformat()


class SafetyRule(BaseModel):
    """安全规则定义。"""

    rule_id: str = Field(..., min_length=1, description="规则 ID")
    name: str = Field(..., min_length=1, description="规则名称")
    stage: SafetyCheckStage = Field(..., description="生效阶段")
    enabled: bool = Field(default=True, description="是否启用")
    severity: SafetySeverity = Field(default="medium", description="风险等级")
    action: SafetyAction = Field(default="allow", description="命中后动作")
    description: str = Field(default="", description="规则说明")
    config: dict[str, Any] = Field(default_factory=dict, description="扩展配置")


class SafetyRuleMatch(BaseModel):
    """规则命中结果。"""

    rule_id: str = Field(..., min_length=1, description="规则 ID")
    rule_name: str = Field(..., min_length=1, description="规则名称")
    severity: SafetySeverity = Field(..., description="风险等级")
    action: SafetyAction = Field(..., description="建议动作")
    reason: str = Field(default="", description="命中原因")


class SafetyCheckRequest(BaseModel):
    """统一安全审查输入。"""

    stage: SafetyCheckStage = Field(..., description="审查阶段")
    task_input: str = Field(default="", description="原始输入文本")
    tool_call: ToolCall | None = Field(default=None, description="工具调用对象")
    final_answer: FinalAnswer | None = Field(default=None, description="最终答案")
    context: dict[str, Any] = Field(default_factory=dict, description="扩展上下文")
    trace_id: str | None = Field(default=None, description="链路 ID")
    run_id: str | None = Field(default=None, description="运行 ID")


class SafetyDecision(BaseModel):
    """统一安全审查输出。"""

    allowed: bool = Field(..., description="是否放行")
    action: SafetyAction = Field(..., description="最终动作")
    stage: SafetyCheckStage = Field(..., description="审查阶段")
    reason: str = Field(default="", description="决策原因")
    reviewer_name: str = Field(..., min_length=1, description="审查器名称")
    reviewer_version: str = Field(..., min_length=1, description="审查器版本")
    policy_version: str = Field(..., min_length=1, description="策略版本")
    triggered_rules: list[SafetyRuleMatch] = Field(default_factory=list, description="命中规则")
    evidence: list[str] = Field(default_factory=list, description="脱敏证据")
    metadata: dict[str, Any] = Field(default_factory=dict, description="附加元数据")
    created_at: str = Field(default_factory=now_iso, description="生成时间")


class SafetyAuditRecord(BaseModel):
    """安全审计记录。"""

    trace_id: str = Field(default="", description="链路 ID")
    run_id: str = Field(default="", description="运行 ID")
    stage: SafetyCheckStage = Field(..., description="审查阶段")
    action: SafetyAction = Field(..., description="最终动作")
    triggered_rules: list[str] = Field(default_factory=list, description="命中规则 ID")
    reason: str = Field(default="", description="审计原因")
    evidence: list[str] = Field(default_factory=list, description="脱敏证据")
    reviewer_name: str = Field(..., min_length=1, description="审查器名称")
    reviewer_version: str = Field(..., min_length=1, description="审查器版本")
    policy_version: str = Field(..., min_length=1, description="策略版本")
    created_at: str = Field(default_factory=now_iso, description="记录时间")


class SafetyReviewer(Protocol):
    """统一审查器协议。"""

    reviewer_name: str
    reviewer_version: str
    policy_version: str
    stage: SafetyCheckStage

    def review(self, request: SafetyCheckRequest) -> SafetyDecision:
        """执行一次安全审查。

        Args:
            request: 标准化审查请求。

        Returns:
            SafetyDecision: 标准化决策结果。
        """
