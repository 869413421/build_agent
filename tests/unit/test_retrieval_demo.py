"""Retrieval 示例脚本测试。"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_demo_module():
    """按文件路径加载 Retrieval 示例脚本。"""

    file_path = Path("examples/retrieval/retrieval_demo.py")
    spec = importlib.util.spec_from_file_location("retrieval_demo", file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 retrieval_demo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_retrieval_demo_should_show_inmemory_result() -> None:
    """示例脚本应展示可离线跑通的 Retrieval 主线结果。"""

    result = _load_demo_module().run_demo()
    inmemory = result["inmemory"]

    assert inmemory["backend_name"] == "inmemory"
    assert inmemory["retriever_version"] == "inmemory-v1"
    assert len(inmemory["hits"]) >= 1
    assert len(inmemory["citations"]) == len(inmemory["hits"])


def test_retrieval_demo_should_gracefully_handle_optional_chroma_path() -> None:
    """示例脚本应在真实向量库路径不可用时给出可解释降级。"""

    result = _load_demo_module().run_demo()
    chroma = result["chroma"]

    assert "available" in chroma
    if chroma["available"]:
        assert chroma["backend_name"] == "chroma"
        assert len(chroma["hits"]) >= 1
    else:
        assert "retrieval-chroma" in chroma["reason"]


def test_retrieval_demo_should_gracefully_handle_chroma_runtime_failure() -> None:
    module = _load_demo_module()
    original = module.ChromaRetriever

    class _BrokenChromaRetriever:
        def __init__(self, *args, **kwargs):
            self.backend_name = "chroma"
            self.retriever_version = "chroma-v1"

        def upsert_documents(self, documents):
            raise ValueError("bad metadata")

    module.ChromaRetriever = _BrokenChromaRetriever
    try:
        result = module.run_chroma_demo()
    finally:
        module.ChromaRetriever = original

    assert result["available"] is False
    assert "Chroma 检索运行失败" in result["reason"]
