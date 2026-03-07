"""Context Engineering 领域模型定义。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agent_forge.components.protocol import AgentMessage


class CitationItem(BaseModel):
    """结构化引用条目。"""

    source_id: str = Field(..., min_length=1, description="引用来源标识。")
    title: str = Field(..., min_length=1, description="引用标题。")
    url: str = Field(..., min_length=1, description="引用链接。")
    snippet: str = Field(default="", description="引用摘要片段。")
    score: float | None = Field(default=None, ge=0.0, le=1.0, description="可选检索分数。")


class ContextBudget(BaseModel):
    """上下文编排的 Token 预算配置。"""

    max_input_tokens: int = Field(default=2048, ge=1, description="模型最大输入 Token。")
    reserved_output_tokens: int = Field(default=512, ge=0, description="预留给输出的 Token。")
    min_latest_user_tokens: int = Field(
        default=64,
        ge=1,
        description="触发截断时，最新用户消息最少保留的 Token。",
    )

    @property
    def available_input_tokens(self) -> int:
        """返回扣除输出预留后的可用输入预算。

        Args:
            None.

        Returns:
            int: 可用输入预算，至少为 1。
        """

        return max(1, self.max_input_tokens - self.reserved_output_tokens)


class BudgetReport(BaseModel):
    """编排预算报告，用于审计与排障。"""

    available_tokens: int = Field(..., ge=1, description="可用输入预算。")
    total_estimated_tokens: int = Field(default=0, ge=0, description="裁剪前估算 Token。")
    kept_estimated_tokens: int = Field(default=0, ge=0, description="裁剪后估算 Token。")
    dropped_estimated_tokens: int = Field(default=0, ge=0, description="被裁掉的估算 Token。")
    kept_messages: int = Field(default=0, ge=0, description="保留消息数量。")
    dropped_messages: int = Field(default=0, ge=0, description="丢弃消息数量。")
    dropped_sections: list[str] = Field(default_factory=list, description="被裁掉的模块及原因。")
    truncated_latest_user: bool = Field(default=False, description="最新用户消息是否被截断。")


class ContextBundle(BaseModel):
    """传递给模型运行时的上下文产物。"""

    system_prompt: str | None = Field(default=None, description="最终 system 提示词。")
    messages: list[AgentMessage] = Field(default_factory=list, description="最终有序消息列表。")
    tools: list[dict[str, Any]] = Field(default_factory=list, description="传给模型的工具列表。")
    citations: list[CitationItem] = Field(default_factory=list, description="被纳入上下文的引用列表。")
    budget_report: BudgetReport = Field(..., description="预算报告。")
