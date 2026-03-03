"""第 4 章 DeepSeek 真实调用演示（流式 + 非流式）。"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from agent_forge.components.model_runtime import DeepSeekAdapter, ModelRequest, ModelRuntime
from agent_forge.components.protocol import AgentMessage
from agent_forge.support.config import settings
from agent_forge.support.logging import get_logger

logger = get_logger(__name__)


def _require_runtime(runtime: ModelRuntime | None) -> ModelRuntime:
    """返回可用 runtime；未注入时创建真实 DeepSeek runtime。"""

    # 1. 优先复用调用方注入的 runtime（便于测试与扩展）。
    if runtime is not None:
        return runtime

    # 2. 真实调用前强校验密钥，避免到网络层才失败。
    if not settings.deepseek_api_key:
        raise RuntimeError("缺少 AF_DEEPSEEK_API_KEY，请先配置环境变量或 .env。")

    # 3. 使用主线组件创建 runtime，确保示例链路与生产链路一致。
    return ModelRuntime(adapter=DeepSeekAdapter(), max_retries=1)


def build_deepseek_request(user_input: str, *, stream: bool) -> ModelRequest:
    """构建 DeepSeek 请求对象。"""

    # 1. 按模式区分输出约束：
    #    - 非流式：要求 JSON 结构，便于教程中的结构化校验。
    #    - 流式：以增量文本输出为主，不强制 JSON schema。
    response_schema: dict[str, Any] | None = None
    if not stream:
        response_schema = {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["answer", "confidence"],
        }

    # 2. 统一模型参数，避免流式/非流式出现行为分叉。
    return ModelRequest(
        messages=[AgentMessage(role="user", content=user_input)],
        model=settings.deepseek_model,
        temperature=0.2,
        max_tokens=512,
        timeout_ms=30000,
        stream=stream,
        response_schema=response_schema,
    )


def run_deepseek_once(user_input: str, runtime: ModelRuntime | None = None) -> dict[str, Any]:
    """执行一次 DeepSeek 非流式调用。"""

    # 1. 准备 runtime 与请求。
    active_runtime = _require_runtime(runtime)
    request = build_deepseek_request(user_input, stream=False)

    # 2. 走非流式主链路。
    response = active_runtime.generate(request)

    # 3. 归一化结果，便于 CLI 与下游复用。
    result = {
        "mode": "non-stream",
        "content": response.content,
        "parsed_output": response.parsed_output,
        "stats": response.stats.model_dump(),
    }

    logger.info(
        "deepseek non-stream completed | total_tokens=%s latency_ms=%s",
        result["stats"]["total_tokens"],
        result["stats"]["latency_ms"],
    )
    return result


def run_deepseek_stream(user_input: str, runtime: ModelRuntime | None = None) -> dict[str, Any]:
    """执行一次 DeepSeek 流式调用，并实时打印增量文本。"""

    # 1. 准备 runtime 与流式请求。
    active_runtime = _require_runtime(runtime)
    request = build_deepseek_request(user_input, stream=True)

    # 2. 消费流式事件并实时输出 delta。
    full_text_parts: list[str] = []
    for event in active_runtime.stream_generate(request):
        if event.event_type == "delta" and event.delta:
            full_text_parts.append(event.delta)
            print(event.delta, end="", flush=True)

    # 3. 统一换行，避免后续 JSON 输出粘连。
    print()

    # 4. 聚合最终响应（由 runtime 统一收敛）。
    response = active_runtime.last_stream_response
    if response is None:
        content = "".join(full_text_parts)
        stats: dict[str, Any] = {}
    else:
        content = response.content or "".join(full_text_parts)
        stats = response.stats.model_dump()

    result = {
        "mode": "stream",
        "content": content,
        "stats": stats,
    }
    logger.info(
        "deepseek stream completed | total_tokens=%s latency_ms=%s",
        result["stats"].get("total_tokens"),
        result["stats"].get("latency_ms"),
    )
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DeepSeek runtime demo（流式 + 非流式）")
    parser.add_argument(
        "prompt",
        nargs="?",
        default="请给出一份劳动仲裁材料准备清单。",
        help="用户输入问题",
    )
    parser.add_argument(
        "--mode",
        choices=["non-stream", "stream", "both"],
        default="both",
        help="运行模式：non-stream / stream / both",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""

    args = parse_args(argv if argv is not None else sys.argv[1:])
    output: dict[str, Any] = {"prompt": args.prompt, "mode": args.mode}

    # 1. 非流式路径：验证结构化输出链路。
    if args.mode in {"non-stream", "both"}:
        output["non_stream"] = run_deepseek_once(args.prompt)

    # 2. 流式路径：验证增量输出链路。
    if args.mode in {"stream", "both"}:
        output["stream"] = run_deepseek_stream(args.prompt)

    # 3. 统一打印最终摘要结果（JSON）。
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
