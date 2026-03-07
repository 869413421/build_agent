"""第八章：Retrieval 可运行示例。"""

from __future__ import annotations

import json
from typing import Any

from agent_forge.components.retrieval import (
    ChromaRetriever,
    InMemoryRetriever,
    RetrievedDocument,
    RetrievalQuery,
    RetrievalRuntime,
)


class LocalHashEmbeddingProvider:
    """示例用本地嵌入器，避免把示例绑死到外部 API。"""

    provider_name = "local-hash"
    provider_version = "local-hash-v1"

    def embed_query(self, text: str) -> list[float]:
        """对查询文本做稳定向量化。

        Args:
            text: 查询文本。

        Returns:
            list[float]: 稳定向量。
        """

        return self._embed(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """对文档列表做稳定向量化。

        Args:
            texts: 文本列表。

        Returns:
            list[list[float]]: 稳定向量列表。
        """

        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        """生成固定维度的简易向量。

        Args:
            text: 原始文本。

        Returns:
            list[float]: 四维示例向量。
        """

        lowered = text.lower()
        return [
            float(len(lowered)),
            float(lowered.count("retrieval")),
            float(lowered.count("vector")),
            float(lowered.count("policy")),
        ]


def build_demo_documents() -> list[RetrievedDocument]:
    """构造示例文档集。

    Returns:
        list[RetrievedDocument]: 示例文档列表。
    """

    return [
        RetrievedDocument(
            document_id="doc-1",
            title="Retrieval Architecture",
            content="Retrieval architecture should keep retriever and reranker pluggable.",
            source_uri="memory://doc-1",
            metadata={"topic": "retrieval"},
        ),
        RetrievedDocument(
            document_id="doc-2",
            title="Vector Database Integration",
            content="Vector database integration should stay behind a stable adapter interface.",
            source_uri="memory://doc-2",
            metadata={"topic": "vector"},
        ),
        RetrievedDocument(
            document_id="doc-3",
            title="Policy Search Notes",
            content="Policy search requires citations that can be forwarded into context engineering.",
            source_uri="memory://doc-3",
            metadata={"topic": "policy"},
        ),
    ]


def run_inmemory_demo() -> dict[str, Any]:
    """运行可离线的基线检索示例。

    Returns:
        dict[str, Any]: 可直接打印或断言的结果。
    """

    # 1. 用内存检索器跑通主线，保证仓库在无外部依赖下也能演示 Retrieval。
    runtime = RetrievalRuntime(InMemoryRetriever(build_demo_documents()))
    result = runtime.search(RetrievalQuery(query_text="retrieval vector adapter", top_k=2))

    # 2. 返回结构化结果，方便测试验证 hits、citations 和版本信息。
    return {
        "backend_name": result.backend_name,
        "retriever_version": result.retriever_version,
        "reranker_version": result.reranker_version,
        "hits": [
            {
                "document_id": item.document.document_id,
                "title": item.document.title,
                "score": item.score,
                "rank": item.rank,
            }
            for item in result.hits
        ],
        "citations": [item.model_dump() for item in result.citations],
    }


def run_chroma_demo() -> dict[str, Any]:
    """运行真实向量库适配示例。

    Returns:
        dict[str, Any]: 若环境支持 Chroma，则返回真实向量检索结果；否则返回可解释的降级结果。
    """

    # 1. 尝试初始化真实向量库适配器；若缺可选依赖，明确返回降级说明而不是直接崩溃。
    embedding_provider = LocalHashEmbeddingProvider()
    try:
        retriever = ChromaRetriever(embedding_provider=embedding_provider)
    except RuntimeError as exc:
        return {
            "available": False,
            "reason": str(exc),
            "hits": [],
        }

    # 2. 写入文档并执行一次真实向量查询；若后端运行失败，同样返回可解释降级结果。
    try:
        retriever.upsert_documents(build_demo_documents())
        hits = retriever.retrieve(RetrievalQuery(query_text="vector adapter", top_k=2))
    except Exception as exc:
        return {
            "available": False,
            "reason": f"Chroma 检索运行失败: {exc}",
            "hits": [],
        }
    return {
        "available": True,
        "backend_name": retriever.backend_name,
        "retriever_version": retriever.retriever_version,
        "hits": [
            {
                "document_id": item.document.document_id,
                "title": item.document.title,
                "score": item.score,
            }
            for item in hits
        ],
    }


def run_demo() -> dict[str, Any]:
    """运行 Retrieval 双路径示例。

    Returns:
        dict[str, Any]: 同时包含基线路径和真实向量库路径结果。
    """

    return {
        "inmemory": run_inmemory_demo(),
        "chroma": run_chroma_demo(),
    }


def print_demo_result(result: dict[str, Any]) -> None:
    """打印示例结果。

    Args:
        result: 结构化示例结果。

    Returns:
        None.
    """

    print("=== inmemory ===")
    print(json.dumps(result["inmemory"], ensure_ascii=False, indent=2))
    print()
    print("=== chroma ===")
    print(json.dumps(result["chroma"], ensure_ascii=False, indent=2))


def main() -> None:
    """运行第八章示例。"""

    # 1. 先跑可离线基线路径，再尝试真实向量库路径。
    result = run_demo()

    # 2. 打印结构化结果，便于教程和测试直接复用。
    print_demo_result(result)


if __name__ == "__main__":
    main()
