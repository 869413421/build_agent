"""Memory 结构化存储实现。"""

from __future__ import annotations

from collections import defaultdict

from agent_forge.components.memory.domain import MemoryReadQuery, MemoryRecord
from agent_forge.components.memory.domain.schemas import now_iso


class _BaseInMemoryMemoryStore:
    """内存结构化存储基类。"""

    def __init__(self) -> None:
        """初始化内存存储。

        Returns:
            None.
        """

        self._records_by_partition: dict[str, dict[str, MemoryRecord]] = defaultdict(dict)

    def upsert(self, records: list[MemoryRecord]) -> list[MemoryRecord]:
        """写入或覆盖记录。

        Args:
            records: 待写入记录。

        Returns:
            list[MemoryRecord]: 实际写入后的记录。
        """

        stored: list[MemoryRecord] = []
        for record in records:
            partition = self._partition_key(record)
            current = self._records_by_partition[partition].get(record.record_key)
            if current is None:
                self._records_by_partition[partition][record.record_key] = record.model_copy(deep=True)
                stored.append(self._records_by_partition[partition][record.record_key].model_copy(deep=True))
                continue
            updated = record.model_copy(
                update={
                    "memory_id": current.memory_id,
                    "created_at": current.created_at,
                    "updated_at": now_iso(),
                    "version": current.version + 1,
                }
            )
            self._records_by_partition[partition][record.record_key] = updated
            stored.append(updated.model_copy(deep=True))
        return stored

    def query(self, query: MemoryReadQuery) -> list[MemoryRecord]:
        """查询记录。

        Args:
            query: 查询请求。

        Returns:
            list[MemoryRecord]: 命中的记录。
        """

        results: list[MemoryRecord] = []
        for record in self._iter_partition_records(query=query):
            if query.categories and record.category not in query.categories:
                continue
            if not query.include_invalidated and record.invalidated:
                continue
            results.append(record.model_copy(deep=True))
        results.sort(key=lambda item: (item.updated_at, item.memory_id), reverse=True)
        return results[: query.top_k]

    def get_by_ids(
        self,
        *,
        tenant_id: str,
        user_id: str,
        session_id: str | None,
        memory_ids: list[str],
        include_invalidated: bool = False,
    ) -> list[MemoryRecord]:
        """按 ID 读取记录。

        Args:
            tenant_id: 租户 ID。
            user_id: 用户 ID。
            session_id: 会话 ID。
            memory_ids: 记忆 ID 列表。
            include_invalidated: 是否包含已失效记录。

        Returns:
            list[MemoryRecord]: 命中的记录。
        """

        query = MemoryReadQuery(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            scope=self._scope_name(),
            top_k=max(len(memory_ids), 1),
            include_invalidated=include_invalidated,
        )
        lookup: dict[str, MemoryRecord] = {}
        for item in self._iter_partition_records(query=query, raw=True):
            if item.memory_id not in memory_ids:
                continue
            if item.invalidated and not include_invalidated:
                continue
            lookup[item.memory_id] = item
        return [lookup[memory_id].model_copy(deep=True) for memory_id in memory_ids if memory_id in lookup]

    def invalidate(
        self,
        *,
        tenant_id: str,
        user_id: str,
        session_id: str | None,
        memory_ids: list[str],
    ) -> int:
        """失效记录。

        Args:
            tenant_id: 租户 ID。
            user_id: 用户 ID。
            session_id: 会话 ID。
            memory_ids: 记忆 ID 列表。

        Returns:
            int: 实际失效数量。
        """

        count = 0
        for record in self._iter_partition_records(
            query=MemoryReadQuery(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                scope=self._scope_name(),
                top_k=max(len(memory_ids), 1),
                include_invalidated=True,
            ),
            raw=True,
        ):
            if record.memory_id not in memory_ids or record.invalidated:
                continue
            record.invalidated = True
            record.updated_at = now_iso()
            count += 1
        return count

    def _iter_partition_records(self, *, query: MemoryReadQuery, raw: bool = False) -> list[MemoryRecord]:
        """遍历查询范围内的记录。

        Args:
            query: 查询请求。
            raw: 是否返回底层对象引用。

        Returns:
            list[MemoryRecord]: 记录列表。
        """

        records: list[MemoryRecord] = []
        for partition in self._partition_candidates(query):
            for record in self._records_by_partition.get(partition, {}).values():
                records.append(record if raw else record.model_copy(deep=True))
        return records

    def _partition_candidates(self, query: MemoryReadQuery) -> list[str]:
        """返回候选分区。

        Args:
            query: 查询请求。

        Returns:
            list[str]: 分区键列表。
        """

        return [self._partition_key_from_query(query)]

    def _partition_key(self, record: MemoryRecord) -> str:
        """由记录生成分区键。

        Args:
            record: 记忆记录。

        Returns:
            str: 分区键。
        """

        raise NotImplementedError

    def _partition_key_from_query(self, query: MemoryReadQuery) -> str:
        """由查询生成分区键。

        Args:
            query: 读取请求。

        Returns:
            str: 分区键。
        """

        raise NotImplementedError

    def _scope_name(self) -> str:
        """返回当前 store scope。

        Returns:
            str: scope 名称。
        """

        raise NotImplementedError


class InMemorySessionMemoryStore(_BaseInMemoryMemoryStore):
    """session 结构化记忆存储。"""

    def _partition_key(self, record: MemoryRecord) -> str:
        return f"{record.tenant_id}:{record.user_id}:{record.session_id}"

    def _partition_key_from_query(self, query: MemoryReadQuery) -> str:
        return f"{query.tenant_id}:{query.user_id}:{query.session_id}"

    def _scope_name(self) -> str:
        return "session"


class InMemoryLongTermMemoryStore(_BaseInMemoryMemoryStore):
    """long-term 结构化记忆存储。"""

    def _partition_key(self, record: MemoryRecord) -> str:
        return f"{record.tenant_id}:{record.user_id}"

    def _partition_key_from_query(self, query: MemoryReadQuery) -> str:
        return f"{query.tenant_id}:{query.user_id}"

    def _scope_name(self) -> str:
        return "long_term"
