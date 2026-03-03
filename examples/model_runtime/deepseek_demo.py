"""第 4 章 DeepSeek 真实调用演示。"""

from __future__ import annotations

import json
import sys
from typing import Any

from agent_forge.components.model_runtime import DeepSeekAdapter, ModelRequest, ModelRuntime
from agent_forge.components.protocol import AgentMessage
from agent_forge.support.config import settings
from agent_forge.support.logging import get_logger

logger = get_logger(__name__)


def build_deepseek_request(user_input: str) -> ModelRequest:
    """构建 DeepSeek 结构化输出请求。"""

    return ModelRequest(
        messages=[AgentMessage(role="user", content=user_input)],
        model=settings.deepseek_model,
        temperature=0.2,
        max_tokens=512,
        timeout_ms=30000,
        response_schema={
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["answer", "confidence"],
        },
    )


def run_deepseek_once(user_input: str, runtime: ModelRuntime | None = None) -> dict[str, Any]:
    """执行一次 DeepSeek 调用并返回标准化结果。"""

    # 1. 确保 runtime 就绪；若未注入则创建真实 DeepSeek runtime。
    if runtime is None:
        if not settings.deepseek_api_key:
            raise RuntimeError("缺少 AF_DEEPSEEK_API_KEY，请先配置环境变量。")
        runtime = ModelRuntime(adapter=DeepSeekAdapter(), max_retries=1)

    # 2. 构建统一请求对象，并声明结构化输出要求。
    request = build_deepseek_request(user_input)

    # 3. 执行 runtime 链路（Adapter 调用 + 可选自愈解析重试）。
    response = runtime.generate(request)

    # 4. 归一化输出，供 CLI 与下游模块复用。
    result = {
        "content": response.content,
        "parsed_output": response.parsed_output,
        "stats": response.stats.model_dump(),
    }

    # 5. 记录一条紧凑摘要日志，便于排障。
    logger.info(
        "deepseek_demo completed | total_tokens=%s latency_ms=%s",
        result["stats"]["total_tokens"],
        result["stats"]["latency_ms"],
    )
    return result


def main(argv: list[str] | None = None) -> int:
    """单次 DeepSeek runtime 演示的 CLI 入口。"""

    args = argv if argv is not None else sys.argv[1:]
    prompt = args[0] if args else "请用一句话介绍你自己。"
    result = run_deepseek_once(prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
