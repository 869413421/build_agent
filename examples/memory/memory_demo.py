"""Memory 组件示例。"""

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
from agent_forge.components.protocol import AgentMessage, FinalAnswer


class DemoModelRuntime:
    """示例用假模型运行时。"""

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        """返回固定结构化抽取结果。

        Args:
            request: 模型请求。
            **kwargs: 额外参数。

        Returns:
            ModelResponse: 固定响应。
        """

        return ModelResponse(
            content='{"items": []}',
            parsed_output={
                "items": [
                    {
                        "scope": "session",
                        "category": "summary",
                        "record_key": "session_summary",
                        "content": "用户本轮想要一份面向 CEO 的周报。",
                        "summary": "CEO 周报请求",
                        "source_excerpt": "面向 CEO 的周报",
                        "metadata": {"origin": "demo"},
                    },
                    {
                        "scope": "long_term",
                        "category": "preference",
                        "record_key": "preference_report_style",
                        "content": "用户偏好简洁、要点式输出。",
                        "summary": "偏好简洁要点式",
                        "source_excerpt": "简洁、要点式输出",
                        "metadata": {"origin": "demo"},
                    },
                ]
            },
            stats=ModelStats(total_tokens=32),
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


def run_demo() -> dict[str, Any]:
    """运行 Memory 示例。

    Returns:
        dict[str, Any]: 示例结果。
    """

    extractor = MemoryExtractor(model_runtime=DemoModelRuntime())
    session_store = InMemorySessionMemoryStore()
    long_term_store = InMemoryLongTermMemoryStore()
    vector_status = "disabled"
    vector_store = None
    try:
        vector_store = ChromaMemoryVectorStore(embedding_provider=LocalHashEmbeddingProvider())
        vector_status = "enabled"
    except RuntimeError as exc:
        vector_status = f"disabled:{exc}"

    runtime = MemoryRuntime(
        extractor=extractor,
        session_store=session_store,
        long_term_store=long_term_store,
        vector_store=vector_store,
    )
    write_result = runtime.write(
        MemoryWriteRequest(
            tenant_id="tenant_demo",
            user_id="user_demo",
            session_id="session_demo",
            trigger="finish",
            messages=[AgentMessage(role="user", content="请帮我生成一份面向 CEO 的简洁周报。")],
            final_answer=FinalAnswer(
                status="success",
                summary="完成周报提炼",
                output={"report_style": "brief", "audience": "CEO"},
            ),
        )
    )
    structured_read = runtime.read(
        MemoryReadQuery(
            tenant_id="tenant_demo",
            user_id="user_demo",
            session_id="session_demo",
            scope="session",
            top_k=5,
        )
    )
    semantic_read = runtime.read(
        MemoryReadQuery(
            tenant_id="tenant_demo",
            user_id="user_demo",
            session_id="session_demo",
            scope="long_term",
            top_k=5,
            query_text="用户喜欢什么输出风格",
        )
    )
    return {
        "vector_status": vector_status,
        "written_count": len(write_result.records),
        "session_records": [item.summary or item.content for item in structured_read.records],
        "long_term_records": [item.summary or item.content for item in semantic_read.records],
    }


if __name__ == "__main__":
    print(run_demo())
