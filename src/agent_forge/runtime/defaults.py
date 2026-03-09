"""`Agent()` 与 `AgentApp()` 使用的默认装配实现。"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any

from agent_forge.components.model_runtime import (
    ModelRequest,
    ModelResponse,
    ModelRuntime,
    ModelStats,
    ModelStreamEvent,
    ProviderAdapter,
)
from agent_forge.components.observability import ObservabilityRuntime
from agent_forge.components.safety import SafetyRuntime, SafetyToolRuntimeHook
from agent_forge.components.tool_runtime import ToolRuntime
from agent_forge.runtime.schemas import AgentConfig


class DefaultAgentAdapter(ProviderAdapter):
    """默认本地模型适配器。

    设计意图：
    1. 保证 `Agent()` 和 `AgentApp()` 在没有外部模型时也能跑通主链路。
    2. 返回稳定的结构化 JSON，便于教程和测试复现。
    3. 这里只提供最小本地桩，不承担真实生产模型能力。
    """

    def generate(self, request: ModelRequest, **kwargs: Any) -> ModelResponse:
        """生成一条结构化模型响应。"""

        _ = kwargs
        # 1. 先从请求消息中抽取最近一次用户输入。
        task_input = _extract_task_input(request)
        # 2. 构造稳定的本地桩输出，保证主链路始终返回合法 JSON。
        content = json.dumps(
            {
                "summary": f"已处理任务：{task_input[:32]}",
                "output": {
                    "answer": f"这是默认本地模型返回的演示答案：{task_input}",
                    "task_input": task_input,
                },
                "references": ["runtime:default-local-adapter"],
            },
            ensure_ascii=False,
        )
        # 3. 返回标准 ModelResponse，交由 AgentRuntime 继续解析与编排。
        return ModelResponse(
            content=content,
            stats=ModelStats(
                prompt_tokens=max(1, len(task_input) // 4),
                completion_tokens=48,
                total_tokens=max(1, len(task_input) // 4) + 48,
                latency_ms=12,
                cost_usd=0.0,
            ),
        )

    def generate_stream(self, request: ModelRequest, **kwargs: Any) -> Iterator[ModelStreamEvent]:
        """输出与 `generate(...)` 对应的演示流式事件。"""

        # 1. 先复用同步生成逻辑，保证流式和非流式内容一致。
        response = self.generate(request, **kwargs)
        request_id = request.request_id or f"req_default_{int(time.time() * 1000)}"
        now_ms = int(time.time() * 1000)
        # 2. 按 start -> delta -> usage -> end 的稳定顺序输出事件。
        yield ModelStreamEvent(event_type="start", request_id=request_id, sequence=0, timestamp_ms=now_ms)
        index = 0
        for index, offset in enumerate(range(0, len(response.content), 16), start=1):
            yield ModelStreamEvent(
                event_type="delta",
                request_id=request_id,
                sequence=index,
                delta=response.content[offset : offset + 16],
                timestamp_ms=int(time.time() * 1000),
            )
        yield ModelStreamEvent(
            event_type="usage",
            request_id=request_id,
            sequence=index + 1 if response.content else 1,
            stats=response.stats,
            timestamp_ms=int(time.time() * 1000),
        )
        yield ModelStreamEvent(
            event_type="end",
            request_id=request_id,
            sequence=index + 2 if response.content else 2,
            content=response.content,
            stats=response.stats,
            timestamp_ms=int(time.time() * 1000),
            metadata={"status": "ok"},
        )


def build_default_model_runtime() -> ModelRuntime:
    """构造默认本地模型运行时。"""

    return ModelRuntime(adapter=DefaultAgentAdapter())


def build_default_observability_runtime() -> ObservabilityRuntime:
    """构造默认观测运行时。"""

    return ObservabilityRuntime()


def build_default_tool_runtime(
    *,
    safety_runtime: SafetyRuntime,
    observability_runtime: ObservabilityRuntime,
) -> ToolRuntime:
    """构造默认工具运行时。

    设计边界：
    1. 默认挂入观测 hook，保留工具执行轨迹。
    2. 默认挂入安全 hook，保证工具前置审查生效。
    """

    # 1. 先创建带观测 hook 的 ToolRuntime。
    tool_runtime = ToolRuntime(hooks=[observability_runtime.build_tool_hook()])
    # 2. 再注册安全 hook，确保工具执行前会经过安全审查。
    tool_runtime.register_hook(
        SafetyToolRuntimeHook(
            safety_runtime,
            spec_resolver=tool_runtime.get_tool_spec,
            capability_resolver=lambda _principal: set(),
        )
    )
    return tool_runtime


def build_default_agent_config() -> AgentConfig:
    """构造默认 Agent 配置。"""

    return AgentConfig()


def _extract_task_input(request: ModelRequest) -> str:
    """从模型请求中提取最近一次用户输入。"""

    # 1. 优先取最近的 user 消息，保持与真实对话语义一致。
    for message in reversed(request.messages):
        if message.role == "user" and message.content.strip():
            return message.content.strip()
    # 2. 如果没有 user 消息，就退回最后一条消息内容。
    return request.messages[-1].content.strip() if request.messages else ""
