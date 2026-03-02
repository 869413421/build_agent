"""Model 组件（大模型契约层）。

目标：
1. 统一请求与响应结构，屏蔽底层厂商差异。
2. 规范化错误类型（超时、限流、解析失败等）。
3. 标准化成本域统计（输入 Token、输出 Token、延迟、成本）。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agent_forge.components.protocol import AgentMessage, ToolCall


class ModelStats(BaseModel):
    """请求统计信息。"""

    prompt_tokens: int = Field(default=0, ge=0, description="输入 Token 数")
    completion_tokens: int = Field(default=0, ge=0, description="输出 Token 数")
    total_tokens: int = Field(default=0, ge=0, description="总 Token 数")
    latency_ms: int = Field(default=0, ge=0, description="请求耗时（毫秒）")
    cost_usd: float | None = Field(default=None, ge=0.0, description="预估成本（美元）")


class ModelRequest(BaseModel):
    """统一模型调用请求。"""

    # 允许通过 `ModelRequest(..., **kwargs)` 直接透传厂商特定参数。
    model_config = ConfigDict(extra="allow")

    messages: list[AgentMessage] = Field(..., description="上下文消息列表")
    system_prompt: str | None = Field(default=None, description="系统提示词（若单独提供）")
    model: str | None = Field(default=None, description="覆盖默认模型名")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="采样温度")
    max_tokens: int | None = Field(default=None, ge=1, description="最大生成 Token 数")
    response_schema: dict[str, Any] | None = Field(default=None, description="期望的 JSON Schema 输出结构")
    tools: list[dict[str, Any]] | None = Field(default=None, description="可用工具列表")
    stream: bool = Field(default=False, description="是否流式返回")

    def extra_kwargs(self) -> dict[str, Any]:
        """返回通过 `**kwargs` 透传的额外参数。"""

        return dict(self.model_extra or {})


class ModelResponse(BaseModel):
    """统一模型调用响应。"""

    content: str = Field(default="", description="响应文本")
    parsed_output: dict[str, Any] | None = Field(default=None, description="结构化解析结果")
    tool_calls: list[ToolCall] = Field(default_factory=list, description="模型决定的工具调用")
    stats: ModelStats = Field(default_factory=ModelStats, description="本次请求统计")


class ModelError(Exception):
    """模型运行时统一异常基类。"""

    def __init__(self, error_code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.retryable = retryable


class ModelTimeoutError(ModelError):
    def __init__(self, message: str = "模型请求超时"):
        super().__init__("MODEL_TIMEOUT", message, retryable=True)


class ModelRateLimitError(ModelError):
    def __init__(self, message: str = "模型请求被限流"):
        super().__init__("MODEL_RATE_LIMIT", message, retryable=True)


class ModelParseError(ModelError):
    def __init__(self, message: str, raw_content: str):
        super().__init__("MODEL_PARSE_ERROR", message, retryable=True)
        self.raw_content = raw_content


class ModelAuthenticationError(ModelError):
    def __init__(self, message: str = "API 密钥无效或未授权"):
        super().__init__("MODEL_AUTH_ERROR", message, retryable=False)


