"""Tool Runtime 示例脚本。"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from typing import Any

from agent_forge.components.protocol import ToolCall
from agent_forge.components.tool_runtime import (
    PythonMathTool,
    TavilySearchTool,
    ToolChainStep,
    ToolRuntime,
    ToolSpec,
    build_python_math_handler,
    build_tavily_search_handler,
)


def create_demo_runtime(tavily_tool: TavilySearchTool | None = None) -> ToolRuntime:
    """创建示例运行时。

    1. 注册 python_math：用于本地可离线验证表达式计算。
    2. 注册 tavily_search：用于外部检索工具接入示例。
    3. 返回完整 runtime：供 CLI 与单测共用，避免重复搭建逻辑。

    Args:
        tavily_tool: 可选 Tavily 工具实例，用于注入 mock client。

    Returns:
        ToolRuntime: 已注册示例工具的运行时。
    """

    runtime = ToolRuntime()
    runtime.register_tool(
        ToolSpec(
            name="python_math",
            args_schema={"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
        ),
        build_python_math_handler(PythonMathTool()),
    )
    runtime.register_tool(
        ToolSpec(
            name="tavily_search",
            args_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}},
                "required": ["query"],
            },
            timeout_ms=20000,
        ),
        build_tavily_search_handler(tavily_tool or TavilySearchTool()),
    )
    return runtime


def run_math_once(expression: str, runtime: ToolRuntime | None = None) -> dict[str, Any]:
    """执行一次数学工具调用并返回结构化结果。

    Args:
        expression: 数学表达式。
        runtime: 可选运行时实例；为空时自动创建。

    Returns:
        dict[str, Any]: 结构化工具结果。
    """

    active_runtime = runtime or create_demo_runtime()
    result = active_runtime.execute(
        ToolCall(
            tool_call_id="demo_math_001",
            tool_name="python_math",
            args={"expression": expression},
            principal="demo",
        )
    )
    return result.model_dump()


def run_tavily_once(query: str, max_results: int = 3, runtime: ToolRuntime | None = None) -> dict[str, Any]:
    """执行一次 Tavily 搜索并返回结构化结果。

    Args:
        query: 搜索查询词。
        max_results: 返回条数上限。
        runtime: 可选运行时实例；为空时自动创建。

    Returns:
        dict[str, Any]: 结构化工具结果。
    """

    active_runtime = runtime or create_demo_runtime()
    result = active_runtime.execute(
        ToolCall(
            tool_call_id="demo_tavily_001",
            tool_name="tavily_search",
            args={"query": query, "max_results": max_results},
            principal="demo",
        )
    )
    return result.model_dump()


def run_tool_chain_once(runtime: ToolRuntime | None = None) -> dict[str, Any]:
    """执行一次工具链示例（seed -> mul）。

    Args:
        runtime: 可选运行时实例；为空时自动创建。

    Returns:
        dict[str, Any]: 工具链执行结果。
    """

    active_runtime = runtime or create_demo_runtime()
    # L-3 修复：幂等注册——已存在则跳过，避免重复调用时抛 ValueError。
    if "seed" not in active_runtime._specs:
        active_runtime.register_tool(ToolSpec(name="seed"), lambda _: {"value": 6})
    if "mul" not in active_runtime._specs:
        active_runtime.register_tool(ToolSpec(name="mul"), lambda args: {"value": args["left"] * args["right"]})

    chain_result = active_runtime.run_chain(
        chain_id="demo_chain_001",
        steps=[
            ToolChainStep(step_id="step_seed", tool_name="seed"),
            ToolChainStep(
                step_id="step_mul",
                tool_name="mul",
                args={"right": 7},
                input_bindings={"left": "step_seed.value"},
            ),
        ],
        principal="demo",
    )
    # 1. JSON 兼容：ToolChainResult.results 内是 ToolResult 对象，需转成 dict 后才能被 json.dumps 序列化。
    # 2. 对外稳定：示例函数直接返回“可打印/可传输”的纯 JSON 结构，避免调用方重复处理。
    return {
        "chain_id": chain_result["chain_id"],
        "status": chain_result["status"],
        "results": [item.model_dump() for item in chain_result["results"]],
        "outputs": chain_result["outputs"],
    }


async def run_math_batch_async(
    expressions: Sequence[str],
    runtime: ToolRuntime | None = None,
    max_concurrency: int = 4,
) -> list[dict[str, Any]]:
    """批量异步执行数学表达式，演示批处理入口。

    Args:
        expressions: 表达式序列。
        runtime: 可选运行时实例；为空时自动创建。
        max_concurrency: 批量执行最大并发。

    Returns:
        list[dict[str, Any]]: 与输入顺序一致的结构化结果列表。
    """

    active_runtime = runtime or create_demo_runtime()
    calls = [
        ToolCall(
            tool_call_id=f"demo_math_batch_{idx + 1}",
            tool_name="python_math",
            args={"expression": expr},
            principal="demo",
        )
        for idx, expr in enumerate(expressions)
    ]
    results = await active_runtime.execute_many_async(calls, max_concurrency=max_concurrency)
    return [item.model_dump() for item in results]


def main() -> None:
    """CLI 入口函数。

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="Tool Runtime demo")
    parser.add_argument("--query", default="agent engineering best practices", help="Tavily query")
    parser.add_argument("--expression", default="sqrt(16) + 2**3", help="math expression")
    parser.add_argument("--skip-tavily", action="store_true", help="skip tavily call")
    parser.add_argument("--batch-math", nargs="*", default=[], help="batch math expressions")
    parser.add_argument("--run-chain", action="store_true", help="run tool chain demo")
    args = parser.parse_args()

    runtime = create_demo_runtime()
    math_result = run_math_once(args.expression, runtime=runtime)
    print("math_result:")
    print(json.dumps(math_result, ensure_ascii=False, indent=2))

    if args.batch_math:
        batch = asyncio.run(run_math_batch_async(args.batch_math, runtime=runtime))
        print("math_batch_result:")
        print(json.dumps(batch, ensure_ascii=False, indent=2))

    if args.run_chain:
        chain_result = run_tool_chain_once(runtime=runtime)
        print("tool_chain_result:")
        print(json.dumps(chain_result, ensure_ascii=False, indent=2))

    if not args.skip_tavily:
        tavily_result = run_tavily_once(args.query, max_results=3, runtime=runtime)
        print("tavily_result:")
        print(json.dumps(tavily_result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
