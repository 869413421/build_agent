"""Memory 组件领域模型。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from agent_forge.components.model_runtime import ModelRequest, ModelResponse
from agent_forge.components.protocol import AgentMessage, AgentState, FinalAnswer, ToolResult


MemoryScope = Literal["session", "long_term"]
MemoryTrigger = Literal["finish", "fact", "preference"]
MemoryCategory = Literal["summary", "fact", "preference", "other"]
MemorySourceType = Literal["final_answer", "agent_message", "tool_result", "retrieval_citation"]


def now_iso() -> str:
    """返回统一的 UTC ISO 时间字符串。

    Returns:
        str: 当前 UTC 时间。
    """

    return datetime.now(timezone.utc).isoformat()


class MemorySource(BaseModel):
    """记忆来源信息。"""

    source_type: MemorySourceType = Field(..., description="来源类型")
    source_id: str | None = Field(default=None, description="来源对象 ID")
    source_excerpt: str = Field(default="", description="来源片段")
    trace_id: str | None = Field(default=None, description="来源 trace_id")
    run_id: str | None = Field(default=None, description="来源 run_id")


class ExtractedMemoryItem(BaseModel):
    """LLM ???????????"""

    scope: MemoryScope = Field(..., description="????")
    category: MemoryCategory = Field(..., description="????")
    record_key: str = Field(..., min_length=1, description="?????")
    content: str = Field(..., min_length=1, description="????")
    summary: str = Field(default="", description="???")
    metadata: dict[str, Any] = Field(default_factory=dict, description="?????")
    source_type: MemorySourceType | None = Field(default=None, description="??????")
    source_id: str | None = Field(default=None, description="???? ID")
    source_excerpt: str = Field(default="", description="????")
    expires_at: str | None = Field(default=None, description="??????")


class MemoryRecord(BaseModel):
    """结构化记忆记录。"""

    memory_id: str = Field(default_factory=lambda: f"mem_{uuid4().hex}", description="记忆 ID")
    record_key: str = Field(..., min_length=1, description="逻辑冲突键")
    scope: MemoryScope = Field(..., description="记忆范围")
    tenant_id: str = Field(..., min_length=1, description="租户隔离键")
    user_id: str = Field(..., min_length=1, description="用户隔离键")
    session_id: str | None = Field(default=None, description="会话隔离键")
    category: MemoryCategory = Field(..., description="记忆类别")
    content: str = Field(..., min_length=1, description="记忆正文")
    summary: str = Field(default="", description="记忆摘要")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    source: MemorySource = Field(..., description="来源信息")
    created_at: str = Field(default_factory=now_iso, description="创建时间")
    updated_at: str = Field(default_factory=now_iso, description="更新时间")
    expires_at: str | None = Field(default=None, description="过期时间")
    version: int = Field(default=1, ge=1, description="版本号")
    invalidated: bool = Field(default=False, description="是否已失效")

    @field_validator("session_id")
    @classmethod
    def _validate_session_id(cls, value: str | None, info: Any) -> str | None:
        """校验 session 记忆必须带 session_id。

        Args:
            value: 输入的 session_id。
            info: Pydantic 校验上下文。

        Returns:
            str | None: 校验后的 session_id。

        Raises:
            ValueError: 当 session 记忆缺少 session_id 时抛出。
        """

        scope = info.data.get("scope")
        if scope == "session" and not value:
            raise ValueError("session scope 的记忆必须提供 session_id")
        return value


class MemoryWriteRequest(BaseModel):
    """Memory 写入请求。"""

    tenant_id: str = Field(..., min_length=1, description="租户隔离键")
    user_id: str = Field(..., min_length=1, description="用户隔离键")
    session_id: str | None = Field(default=None, description="会话隔离键")
    trigger: MemoryTrigger = Field(..., description="写入触发器")
    agent_state: AgentState | None = Field(default=None, description="完整运行状态")
    final_answer: FinalAnswer | None = Field(default=None, description="最终答案")
    messages: list[AgentMessage] = Field(default_factory=list, description="辅助消息")
    tool_results: list[ToolResult] = Field(default_factory=list, description="辅助工具结果")
    extracted_items: list[ExtractedMemoryItem] = Field(default_factory=list, description="已抽取记忆项")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    trace_id: str | None = Field(default=None, description="来源 trace_id")
    run_id: str | None = Field(default=None, description="来源 run_id")


class MemoryWriteResult(BaseModel):
    """Memory 写入结果。"""

    records: list[MemoryRecord] = Field(default_factory=list, description="写入后的最终记录")
    extracted_count: int = Field(default=0, ge=0, description="抽取出的记忆项数量")
    structured_written_count: int = Field(default=0, ge=0, description="结构化写入数")
    vector_written_count: int = Field(default=0, ge=0, description="向量写入数")
    trigger: MemoryTrigger = Field(..., description="本次触发器")
    trace_id: str | None = Field(default=None, description="trace_id")
    run_id: str | None = Field(default=None, description="run_id")


class MemoryReadQuery(BaseModel):
    """Memory 读取请求。"""

    tenant_id: str = Field(..., min_length=1, description="租户隔离键")
    user_id: str = Field(..., min_length=1, description="用户隔离键")
    session_id: str | None = Field(default=None, description="会话隔离键")
    scope: MemoryScope | None = Field(default=None, description="读取范围")
    categories: list[MemoryCategory] = Field(default_factory=list, description="限定类别")
    top_k: int = Field(default=5, ge=1, description="返回上限")
    include_invalidated: bool = Field(default=False, description="是否包含已失效记录")
    query_text: str | None = Field(default=None, description="语义检索文本")


class MemoryReadResult(BaseModel):
    """Memory 读取结果。"""

    records: list[MemoryRecord] = Field(default_factory=list, description="读取结果")
    total_matched: int = Field(default=0, ge=0, description="匹配总数")
    scope: MemoryScope | None = Field(default=None, description="实际范围")
    from_vector_search: bool = Field(default=False, description="是否来自向量查询")
    read_trace: dict[str, Any] = Field(default_factory=dict, description="最小解释信息")


class MemoryVectorDocument(BaseModel):
    """向量库存储文档。"""

    memory_id: str = Field(..., min_length=1, description="记忆 ID")
    text: str = Field(..., min_length=1, description="向量化文本")
    metadata: dict[str, Any] = Field(default_factory=dict, description="向量元数据")


class MemoryVectorHit(BaseModel):
    """向量命中结果。"""

    memory_id: str = Field(..., min_length=1, description="命中的记忆 ID")
    score: float = Field(default=0.0, description="相似度分数")
    metadata: dict[str, Any] = Field(default_factory=dict, description="命中元数据")


class MemoryStructuredStore(Protocol):
    """结构化记忆存储接口。"""

    def upsert(self, records: list[MemoryRecord]) -> list[MemoryRecord]:
        """写入或覆盖结构化记忆。

        Args:
            records: 待写入记录。

        Returns:
            list[MemoryRecord]: 实际持久化后的记录。
        """

    def query(self, query: MemoryReadQuery) -> list[MemoryRecord]:
        """查询结构化记忆。

        Args:
            query: 查询请求。

        Returns:
            list[MemoryRecord]: 命中的记录。
        """

    def get_by_ids(
        self,
        *,
        tenant_id: str,
        user_id: str,
        session_id: str | None,
        memory_ids: list[str],
        include_invalidated: bool = False,
    ) -> list[MemoryRecord]:
        """按 ID 批量读取。

        Args:
            tenant_id: 租户 ID。
            user_id: 用户 ID。
            session_id: 会话 ID。
            memory_ids: 记忆 ID 列表。
            include_invalidated: 是否包含已失效记录。

        Returns:
            list[MemoryRecord]: 命中的记录。
        """

    def invalidate(
        self,
        *,
        tenant_id: str,
        user_id: str,
        session_id: str | None,
        memory_ids: list[str],
    ) -> int:
        """失效指定记录。

        Args:
            tenant_id: 租户 ID。
            user_id: 用户 ID。
            session_id: 会话 ID。
            memory_ids: 记忆 ID 列表。

        Returns:
            int: 实际失效数量。
        """


class MemoryVectorStore(Protocol):
    """向量记忆存储接口。"""

    backend_name: str
    backend_version: str

    def upsert(self, records: list[MemoryRecord]) -> int:
        """写入向量记忆。

        Args:
            records: 待写入记录。

        Returns:
            int: 实际写入数量。
        """

    def query(self, query: MemoryReadQuery) -> list[MemoryVectorHit]:
        """执行向量查询。

        Args:
            query: 查询请求。

        Returns:
            list[MemoryVectorHit]: 命中结果。
        """

    def invalidate(
        self,
        *,
        tenant_id: str,
        user_id: str,
        session_id: str | None,
        memory_ids: list[str],
    ) -> int:
        """失效向量记忆。

        Args:
            tenant_id: 租户 ID。
            user_id: 用户 ID。
            session_id: 会话 ID。
            memory_ids: 记忆 ID 列表。

        Returns:
            int: 实际失效数量。
        """


class MemoryModelRuntime(Protocol):
    """供 MemoryExtractor 使用的最小模型运行时接口。"""

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        """执行结构化抽取。

        Args:
            request: 模型请求。
            **kwargs: 运行时参数。

        Returns:
            ModelResponse: 结构化抽取响应。
        """
