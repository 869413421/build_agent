"""Evaluator 领域模型。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from agent_forge.components.model_runtime import ModelRequest, ModelResponse
from agent_forge.components.protocol import AgentState, ExecutionEvent, FinalAnswer


EvaluationMode = Literal["output", "trajectory", "combined"]
EvaluationVerdict = Literal["pass", "warning", "fail"]
EvaluationDimension = Literal[
    "correctness",
    "groundedness",
    "completeness",
    "instruction_following",
    "tool_effectiveness",
    "efficiency",
    "memory_usefulness",
]


def now_iso() -> str:
    """返回统一的 UTC 时间字符串。"""

    return datetime.now(timezone.utc).isoformat()


class EvaluationRubric(BaseModel):
    """评估 rubric。"""

    name: str = Field(..., min_length=1, description="rubric 名称")
    dimensions: list[EvaluationDimension] = Field(default_factory=list, description="启用的评估维度")
    weights: dict[EvaluationDimension, float] = Field(default_factory=dict, description="维度权重")
    pass_threshold: float = Field(default=0.75, ge=0.0, le=1.0, description="通过阈值")
    instructions: str = Field(default="", description="补充评估说明")


class EvaluationScore(BaseModel):
    """单维度评分。"""

    dimension: EvaluationDimension = Field(..., description="评估维度")
    score: float = Field(..., ge=0.0, le=1.0, description="归一化分数")
    reason: str = Field(default="", description="评分理由")
    evidence: list[str] = Field(default_factory=list, description="证据片段")


class TrajectorySummary(BaseModel):
    """执行轨迹摘要。"""

    total_events: int = Field(default=0, ge=0, description="事件总数")
    total_tool_calls: int = Field(default=0, ge=0, description="工具调用数")
    total_tool_errors: int = Field(default=0, ge=0, description="工具错误数")
    total_replans: int = Field(default=0, ge=0, description="replan 次数")
    total_errors: int = Field(default=0, ge=0, description="error 事件数")
    unique_event_types: list[str] = Field(default_factory=list, description="事件类型列表")
    notes: list[str] = Field(default_factory=list, description="轨迹观察备注")


class EvaluationResult(BaseModel):
    """评估结果。"""

    verdict: EvaluationVerdict = Field(..., description="总体判定")
    total_score: float = Field(..., ge=0.0, le=1.0, description="总分")
    scores: list[EvaluationScore] = Field(default_factory=list, description="维度评分明细")
    summary: str = Field(default="", description="总体摘要")
    strengths: list[str] = Field(default_factory=list, description="优点")
    weaknesses: list[str] = Field(default_factory=list, description="缺点")
    suggestions: list[str] = Field(default_factory=list, description="优化建议")
    evaluator_name: str = Field(..., min_length=1, description="评估器名称")
    evaluator_version: str = Field(..., min_length=1, description="评估器版本")
    mode: EvaluationMode = Field(..., description="评估模式")
    trace_id: str | None = Field(default=None, description="trace_id")
    run_id: str | None = Field(default=None, description="run_id")
    metadata: dict[str, Any] = Field(default_factory=dict, description="附加信息")
    created_at: str = Field(default_factory=now_iso, description="结果生成时间")


class EvaluationRequest(BaseModel):
    """评估请求。"""

    trace_id: str | None = Field(default=None, description="trace_id")
    run_id: str | None = Field(default=None, description="run_id")
    task_input: str = Field(default="", description="任务输入")
    final_answer: FinalAnswer | None = Field(default=None, description="最终答案")
    agent_state: AgentState | None = Field(default=None, description="完整状态")
    events: list[ExecutionEvent] = Field(default_factory=list, description="执行事件")
    expected_answer: str | None = Field(default=None, description="期望答案")
    reference_facts: list[str] = Field(default_factory=list, description="参考事实")
    rubric: EvaluationRubric | None = Field(default=None, description="rubric")
    mode: EvaluationMode = Field(default="combined", description="评估模式")


class Evaluator(Protocol):
    """统一评估器协议。"""

    evaluator_name: str
    evaluator_version: str

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """执行一次评估。"""


class EvaluatorModelRuntime(Protocol):
    """给 LLM judge 复用的最小 ModelRuntime 协议。"""

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        """执行结构化 judge 调用。"""
