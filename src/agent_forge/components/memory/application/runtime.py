"""Memory 运行时。"""

from __future__ import annotations

from collections import defaultdict

from agent_forge.components.memory.application.extractor import MemoryExtractor
from agent_forge.components.memory.domain import (
    MemoryReadQuery,
    MemoryReadResult,
    MemoryRecord,
    MemoryScope,
    MemoryStructuredStore,
    MemoryTrigger,
    MemoryVectorStore,
    MemoryWriteRequest,
    MemoryWriteResult,
    MemorySource,
)


class MemoryRuntime:
    """统一编排抽取、结构化存储和向量存储。"""

    def __init__(
        self,
        *,
        extractor: MemoryExtractor,
        session_store: MemoryStructuredStore,
        long_term_store: MemoryStructuredStore,
        vector_store: MemoryVectorStore | None = None,
    ) -> None:
        """初始化 MemoryRuntime。

        Args:
            extractor: 记忆抽取器。
            session_store: session 结构化存储。
            long_term_store: long-term 结构化存储。
            vector_store: 可选向量存储。

        Returns:
            None.
        """

        self._extractor = extractor
        self._session_store = session_store
        self._long_term_store = long_term_store
        self._vector_store = vector_store

    def write(self, request: MemoryWriteRequest) -> MemoryWriteResult:
        """执行一次记忆写入。

        Args:
            request: 写入请求。

        Returns:
            MemoryWriteResult: 最终写入结果。
        """

        # 1. 先校验隔离键，避免 Memory 组件默认兜底导致跨租户串写。
        _validate_write_request(request)

        # 2. 再按 trigger 调用抽取器，得到标准化的记忆项。
        extracted_items = self._extractor.extract(request)
        if not extracted_items:
            return MemoryWriteResult(
                trigger=request.trigger,
                trace_id=request.trace_id,
                run_id=request.run_id,
            )

        # 3. 把抽取项转换成结构化记录，并写入对应 scope 的 store。
        records = [self._build_record(request=request, item=item) for item in extracted_items]
        stored_records = self._write_structured_records(records)

        # 4. 最后把已确认持久化的记录同步写入向量库，保证结构化层是真源。
        vector_written_count = 0
        if self._vector_store is not None:
            vector_written_count = self._vector_store.upsert(stored_records)

        return MemoryWriteResult(
            records=stored_records,
            extracted_count=len(extracted_items),
            structured_written_count=len(stored_records),
            vector_written_count=vector_written_count,
            trigger=request.trigger,
            trace_id=request.trace_id,
            run_id=request.run_id,
        )

    def read(self, query: MemoryReadQuery) -> MemoryReadResult:
        """读取记忆。

        Args:
            query: 查询请求。

        Returns:
            MemoryReadResult: 读取结果。
        """

        # 1. 先校验隔离键，避免读路径出现跨租户泄漏。
        _validate_read_query(query)

        # 2. 有 query_text 且配置了向量库时，先走语义召回，再回填结构化记录。
        if query.query_text and self._vector_store is not None:
            hits = self._query_vector(query)
            records = self._get_records_by_vector_hits(query=query, hits=hits)
            return MemoryReadResult(
                records=records,
                total_matched=len(records),
                scope=query.scope,
                from_vector_search=True,
                read_trace={
                    "mode": "vector",
                    "backend_name": self._vector_store.backend_name,
                    "backend_version": self._vector_store.backend_version,
                    "matched_memory_ids": [item.memory_id for item in hits],
                },
            )

        # 3. 否则走结构化读取，保持 explainable read 的可预测语义。
        records = self._query_structured(query)
        return MemoryReadResult(
            records=records,
            total_matched=len(records),
            scope=query.scope,
            from_vector_search=False,
            read_trace={
                "mode": "structured",
                "scopes": _resolved_scopes(query.scope, query.session_id),
            },
        )

    def invalidate(
        self,
        *,
        tenant_id: str,
        user_id: str,
        session_id: str | None,
        memory_ids: list[str],
    ) -> int:
        """失效指定记忆。

        Args:
            tenant_id: 租户 ID。
            user_id: 用户 ID。
            session_id: 会话 ID。
            memory_ids: 待失效记忆 ID。

        Returns:
            int: 实际失效数量。
        """

        count = 0
        count += self._session_store.invalidate(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            memory_ids=memory_ids,
        )
        count += self._long_term_store.invalidate(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=None,
            memory_ids=memory_ids,
        )
        if self._vector_store is not None:
            self._vector_store.invalidate(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                memory_ids=memory_ids,
            )
        return count

    def _build_record(self, *, request: MemoryWriteRequest, item: object) -> MemoryRecord:
        """把抽取结果转换为记忆记录。

        Args:
            request: 写入请求。
            item: 抽取项。

        Returns:
            MemoryRecord: 结构化记忆记录。
        """

        source = MemorySource(
            source_type=getattr(item, "source_type", None) or _resolve_source_type(request.trigger),
            source_id=getattr(item, "source_id", None),
            source_excerpt=getattr(item, "source_excerpt"),
            trace_id=request.trace_id or (request.agent_state.trace_id if request.agent_state else None),
            run_id=request.run_id or (request.agent_state.run_id if request.agent_state else None),
        )
        return MemoryRecord(
            record_key=getattr(item, "record_key"),
            scope=getattr(item, "scope"),
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            session_id=request.session_id if getattr(item, "scope") == "session" else None,
            category=getattr(item, "category"),
            content=getattr(item, "content"),
            summary=getattr(item, "summary"),
            metadata={**request.metadata, **getattr(item, "metadata")},
            source=source,
            expires_at=getattr(item, "expires_at"),
        )

    def _write_structured_records(self, records: list[MemoryRecord]) -> list[MemoryRecord]:
        """写入结构化存储。

        Args:
            records: 待写入记录。

        Returns:
            list[MemoryRecord]: 实际写入后的记录。
        """

        grouped: dict[MemoryScope, list[MemoryRecord]] = defaultdict(list)
        for record in records:
            grouped[record.scope].append(record)

        stored: list[MemoryRecord] = []
        if grouped["session"]:
            stored.extend(self._session_store.upsert(grouped["session"]))
        if grouped["long_term"]:
            stored.extend(self._long_term_store.upsert(grouped["long_term"]))
        stored.sort(key=lambda item: (item.updated_at, item.memory_id), reverse=True)
        return stored

    def _query_vector(self, query: MemoryReadQuery) -> list[object]:
        """æç»ä¸ scope è¯­ä¹æ§è¡åéæ¥è¯¢ã

        Args:
            query: æ¥è¯¢è¯·æ±ã

        Returns:
            list[object]: åéå½ä¸­ç»æã
        """

        if query.scope is not None:
            return self._vector_store.query(query)
        if query.session_id:
            session_hits = self._vector_store.query(query.model_copy(update={"scope": "session"}))
            long_term_hits = self._vector_store.query(
                query.model_copy(update={"scope": "long_term", "session_id": None})
            )
            return _merge_vector_hits(session_hits, long_term_hits, top_k=query.top_k)
        return self._vector_store.query(query.model_copy(update={"scope": "long_term", "session_id": None}))

    def _query_structured(self, query: MemoryReadQuery) -> list[MemoryRecord]:
        """æç»ä¸ scope è¯­ä¹æ¥è¯¢ç»æåå­å¨ã

        Args:
            query: æ¥è¯¢è¯·æ±ã

        Returns:
            list[MemoryRecord]: ç»æåå½ä¸­ã
        """

        output: list[MemoryRecord] = []
        if query.scope == "session":
            output.extend(self._session_store.query(query))
        elif query.scope == "long_term":
            output.extend(self._long_term_store.query(query.model_copy(update={"session_id": None, "scope": "long_term"})))
        elif query.session_id:
            output.extend(self._session_store.query(query.model_copy(update={"scope": "session"})))
            output.extend(
                self._long_term_store.query(query.model_copy(update={"session_id": None, "scope": "long_term"}))
            )
        else:
            output.extend(self._long_term_store.query(query.model_copy(update={"session_id": None, "scope": "long_term"})))
        output.sort(key=lambda item: (item.updated_at, item.memory_id), reverse=True)
        return output[: query.top_k]

    def _get_records_by_vector_hits(self, *, query: MemoryReadQuery, hits: list[object]) -> list[MemoryRecord]:
        """æåéå½ä¸­åå¡«ä¸ºç»æåè®°å½ã

        Args:
            query: æ¥è¯¢è¯·æ±ã
            hits: åéå½ä¸­ç»æã

        Returns:
            list[MemoryRecord]: å¯¹åºè®°å½ã
        """

        if not hits:
            return []

        memory_ids = [str(getattr(item, "memory_id")) for item in hits]
        lookup: dict[str, MemoryRecord] = {}
        if query.scope == "session":
            for item in self._session_store.get_by_ids(
                tenant_id=query.tenant_id,
                user_id=query.user_id,
                session_id=query.session_id,
                memory_ids=memory_ids,
                include_invalidated=query.include_invalidated,
            ):
                lookup[item.memory_id] = item
        elif query.scope == "long_term":
            for item in self._long_term_store.get_by_ids(
                tenant_id=query.tenant_id,
                user_id=query.user_id,
                session_id=None,
                memory_ids=memory_ids,
                include_invalidated=query.include_invalidated,
            ):
                lookup[item.memory_id] = item
        elif query.session_id:
            for item in self._session_store.get_by_ids(
                tenant_id=query.tenant_id,
                user_id=query.user_id,
                session_id=query.session_id,
                memory_ids=memory_ids,
                include_invalidated=query.include_invalidated,
            ):
                lookup[item.memory_id] = item
            for item in self._long_term_store.get_by_ids(
                tenant_id=query.tenant_id,
                user_id=query.user_id,
                session_id=None,
                memory_ids=memory_ids,
                include_invalidated=query.include_invalidated,
            ):
                lookup[item.memory_id] = item
        else:
            for item in self._long_term_store.get_by_ids(
                tenant_id=query.tenant_id,
                user_id=query.user_id,
                session_id=None,
                memory_ids=memory_ids,
                include_invalidated=query.include_invalidated,
            ):
                lookup[item.memory_id] = item
        return [lookup[memory_id] for memory_id in memory_ids if memory_id in lookup][: query.top_k]



def _validate_write_request(request: MemoryWriteRequest) -> None:
    """校验写入请求。

    Args:
        request: 写入请求。

    Returns:
        None.

    Raises:
        ValueError: 当隔离键非法时抛出。
    """

    if not request.tenant_id.strip():
        raise ValueError("tenant_id 不能为空")
    if not request.user_id.strip():
        raise ValueError("user_id 不能为空")
    if request.trigger in {"finish", "fact", "preference"} and not request.session_id:
        raise ValueError("Memory 首版写入必须提供 session_id")


def _validate_read_query(query: MemoryReadQuery) -> None:
    """校验读取请求。

    Args:
        query: 读取请求。

    Returns:
        None.

    Raises:
        ValueError: 当隔离键非法时抛出。
    """

    if not query.tenant_id.strip():
        raise ValueError("tenant_id 不能为空")
    if not query.user_id.strip():
        raise ValueError("user_id 不能为空")
    if query.scope == "session" and not query.session_id:
        raise ValueError("读取 session memory 时必须提供 session_id")


def _resolved_scopes(scope: MemoryScope | None, session_id: str | None) -> list[MemoryScope]:
    """æ scope åæ°è§£æä¸ºå®é
è®¿é®èå´ã

    Args:
        scope: 显式传入的 scope。
        session_id: å½åæ¥è¯¢æºå¸¦ç session_idã

    Returns:
        list[MemoryScope]: è§£æåçèå´ã
    """

    if scope is not None:
        return [scope]
    if session_id:
        return ["session", "long_term"]
    return ["long_term"]


def _merge_vector_hits(*groups: list[object], top_k: int) -> list[object]:
    """åå¹¶å¤è·¯åéå½ä¸­ï¼å¹¶æ score å»éæåºã

    Args:
        *groups: å¤ç»åéå½ä¸­ã
        top_k: æç»ä¿çæ°éã

    Returns:
        list[object]: åå¹¶åçå½ä¸­åè¡¨ã
    """

    lookup: dict[str, object] = {}
    scores: dict[str, float] = {}
    for group in groups:
        for hit in group:
            memory_id = str(getattr(hit, "memory_id"))
            score = float(getattr(hit, "score", 0.0))
            if memory_id in scores and scores[memory_id] >= score:
                continue
            lookup[memory_id] = hit
            scores[memory_id] = score
    merged = list(lookup.values())
    merged.sort(key=lambda item: (-float(getattr(item, "score", 0.0)), str(getattr(item, "memory_id"))))
    return merged[:top_k]


def _resolve_source_type(trigger: MemoryTrigger) -> str:
    """把 trigger 映射到默认来源类型。

    Args:
        trigger: 写入触发器。

    Returns:
        str: 来源类型。
    """

    if trigger == "finish":
        return "final_answer"
    if trigger == "fact":
        return "tool_result"
    return "agent_message"
