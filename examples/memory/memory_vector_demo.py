"""Memory 向量检索示例。"""

from __future__ import annotations

from typing import Any

from agent_forge.components.memory import (
    ChromaMemoryVectorStore,
    MemoryExtractor,
    MemoryReadQuery,
    MemoryRuntime,
    MemoryWriteRequest,
    InMemoryLongTermMemoryStore,
    InMemorySessionMemoryStore,
)
from agent_forge.components.model_runtime import ModelRequest, ModelResponse, ModelStats


class DemoVectorModelRuntime:
    """返回固定长期记忆的假模型运行时。"""

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        """返回固定抽取结果。

        Args:
            request: 模型请求。
            **kwargs: 额外参数。

        Returns:
            ModelResponse: 结构化抽取结果。
        """

        return ModelResponse(
            content='{"items": []}',
            parsed_output={
                "items": [
                    {
                        "scope": "long_term",
                        "category": "preference",
                        "record_key": "pref_tone",
                        "content": "用户偏好正式、简洁、结论前置的汇报风格。",
                        "summary": "偏好正式简洁结论前置",
                        "source_excerpt": "正式、简洁、结论前置",
                        "metadata": {"origin": "vector_demo"},
                    }
                ]
            },
            stats=ModelStats(total_tokens=24),
        )


class LocalHashEmbeddingProvider:
    """示例本地 embedding provider。"""

    provider_name = "local-hash"
    provider_version = "local-hash-v1"

    def embed_query(self, text: str) -> list[float]:
        """生成查询向量。

        Args:
            text: 输入文本。

        Returns:
            list[float]: 简单向量。
        """

        return [float(len(text)), float(sum(ord(ch) for ch in text) % 97)]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """生成文档向量。

        Args:
            texts: 文本列表。

        Returns:
            list[list[float]]: 简单向量列表。
        """

        return [self.embed_query(text) for text in texts]


class FakeCollection:
    """最小 Chroma collection 假实现。"""

    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}

    def upsert(
        self,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        """写入记录。

        Args:
            ids: 文档 ID。
            documents: 文本内容。
            metadatas: 元数据。
            embeddings: 向量。

        Returns:
            None.
        """

        for index, memory_id in enumerate(ids):
            self.records[memory_id] = {
                "document": documents[index],
                "metadata": metadatas[index],
                "embedding": embeddings[index],
            }

    def query(
        self,
        *,
        query_embeddings: list[list[float]],
        n_results: int,
        include: list[str],
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """执行最小相似度查询。

        Args:
            query_embeddings: 查询向量。
            n_results: 返回数量。
            include: 返回字段。
            where: 过滤条件。

        Returns:
            dict[str, Any]: 模拟 Chroma 结果。
        """

        _ = include
        query_vector = query_embeddings[0]
        candidates: list[tuple[str, dict[str, Any], float]] = []
        for memory_id, payload in self.records.items():
            metadata = payload["metadata"]
            if where and not _matches_where(metadata, where):
                continue
            embedding = payload["embedding"]
            distance = abs(query_vector[0] - embedding[0]) + abs(query_vector[1] - embedding[1])
            candidates.append((memory_id, metadata, distance))
        candidates.sort(key=lambda item: item[2])
        picked = candidates[:n_results]
        return {
            "ids": [[item[0] for item in picked]],
            "metadatas": [[item[1] for item in picked]],
            "distances": [[item[2] for item in picked]],
        }


def _matches_where(metadata: dict[str, Any], where: dict[str, Any]) -> bool:
    """解析 where 条件，模拟 Chroma 的 metadata 过滤行为。

    Args:
        metadata: 当前候选记录的 metadata。
        where: Chroma 风格的 where 条件。

    Returns:
        bool: 当前 metadata 是否满足过滤条件。
    """

    if "$and" in where:
        return all(_matches_where(metadata, condition) for condition in where["$and"] if isinstance(condition, dict))
    for key, expected in where.items():
        if isinstance(expected, dict) and "$in" in expected:
            if metadata.get(key) not in expected["$in"]:
                return False
            continue
        if metadata.get(key) != expected:
            return False
    return True


def run_vector_demo() -> dict[str, Any]:
    """运行向量检索示例。

    Returns:
        dict[str, Any]: 示例结果。
    """

    runtime = MemoryRuntime(
        extractor=MemoryExtractor(model_runtime=DemoVectorModelRuntime()),
        session_store=InMemorySessionMemoryStore(),
        long_term_store=InMemoryLongTermMemoryStore(),
        vector_store=ChromaMemoryVectorStore(
            collection=FakeCollection(),
            embedding_provider=LocalHashEmbeddingProvider(),
        ),
    )
    write_result = runtime.write(
        MemoryWriteRequest(
            tenant_id="tenant_demo",
            user_id="user_demo",
            session_id="session_demo",
            trigger="preference",
        )
    )
    read_result = runtime.read(
        MemoryReadQuery(
            tenant_id="tenant_demo",
            user_id="user_demo",
            session_id="session_demo",
            scope="long_term",
            top_k=3,
            query_text="用户喜欢什么汇报风格",
        )
    )
    return {
        "written_count": len(write_result.records),
        "vector_match_count": len(read_result.records),
        "matched_summaries": [item.summary for item in read_result.records],
        "read_mode": read_result.read_trace.get("mode"),
    }


if __name__ == "__main__":
    print(run_vector_demo())
