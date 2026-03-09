"""`AgentApp` 应用级注册与装配入口。"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from agent_forge.components.engine import EngineLoop
from agent_forge.components.evaluator import EvaluatorRuntime
from agent_forge.components.model_runtime import ModelRuntime
from agent_forge.components.observability import ObservabilityRuntime
from agent_forge.components.retrieval import RetrievalRuntime
from agent_forge.components.safety import SafetyRuntime
from agent_forge.components.tool_runtime import ToolRuntime, ToolSpec
from agent_forge.runtime.agent import Agent
from agent_forge.runtime.defaults import (
    build_default_model_runtime,
    build_default_observability_runtime,
    build_default_tool_runtime,
)
from agent_forge.runtime.runtime import AgentRuntime
from agent_forge.runtime.schemas import AgentConfig

ToolHandler = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class AgentAppTool:
    """封装 `AgentApp` 中注册的一条工具定义。"""

    spec: ToolSpec
    handler: ToolHandler


class AgentApp:
    """应用级 registry / factory。

    设计边界：
    1. `AgentApp` 负责注册共享能力，不负责执行编排。
    2. `AgentApp` 通过 `create_agent(...)` 组装 `Agent -> AgentRuntime` 链路。
    3. 工具采用“全局注册 + agent 授权子集”的装配模型。
    """

    def __init__(
        self,
        *,
        config: AgentConfig | None = None,
        observability_runtime: ObservabilityRuntime | None = None,
        safety_runtime: SafetyRuntime | None = None,
    ) -> None:
        """初始化应用级注册中心。"""

        self.config = config or AgentConfig()
        self.observability_runtime = observability_runtime or build_default_observability_runtime()
        self.default_safety_runtime = safety_runtime or SafetyRuntime()
        self._models: dict[str, ModelRuntime] = {"default": build_default_model_runtime()}
        self._tools: dict[str, AgentAppTool] = {}
        self._memories: dict[str, Any] = {}
        self._retrievals: dict[str, RetrievalRuntime] = {}
        self._evaluators: dict[str, EvaluatorRuntime] = {}
        self._safeties: dict[str, SafetyRuntime] = {}

    def register_model(self, name: str, runtime: ModelRuntime) -> None:
        """注册模型运行时。"""

        self._register_named(self._models, name, runtime, kind="model", allow_replace=True)

    def register_tools(self, tools: Iterable[Any]) -> None:
        """批量注册工具池。"""

        for tool in tools:
            normalized = self._normalize_tool(tool)
            self._register_named(self._tools, normalized.spec.name, normalized, kind="tool")

    def register_memory(self, name: str, runtime: Any) -> None:
        """注册 memory runtime。

        首版约束：
        1. 这里只接受已经封装好的 runtime。
        2. runtime 必须同时提供 `read(...)` 与 `write(...)`。
        """

        self._validate_memory_runtime(runtime)
        self._register_named(self._memories, name, runtime, kind="memory")

    def register_retrieval(self, name: str, runtime: RetrievalRuntime) -> None:
        """注册 retrieval runtime。"""

        self._register_named(self._retrievals, name, runtime, kind="retrieval")

    def register_evaluator(self, name: str, runtime: EvaluatorRuntime) -> None:
        """注册 evaluator runtime。"""

        self._register_named(self._evaluators, name, runtime, kind="evaluator")

    def register_safety(self, name: str, runtime: SafetyRuntime) -> None:
        """注册 safety runtime。"""

        self._register_named(self._safeties, name, runtime, kind="safety")

    def create_agent(
        self,
        *,
        name: str,
        model: str,
        allowed_tools: list[str] | None = None,
        memory: str | None = None,
        retrieval: str | None = None,
        evaluator: str | None = None,
        safety: str | None = None,
        agent_cls: type[Agent] | None = None,
        config: AgentConfig | None = None,
        engine_loop: EngineLoop | None = None,
    ) -> Agent:
        """按名字解析依赖并创建一个 `Agent`。"""

        # 1. 解析本次 agent 的基础配置与共享能力实例。
        agent_config = config or self.config
        agent_type = agent_cls or Agent
        model_runtime = self._resolve_named(self._models, model, kind="model")
        retrieval_runtime = self._resolve_optional(self._retrievals, retrieval, kind="retrieval")
        evaluator_runtime = self._resolve_optional(self._evaluators, evaluator, kind="evaluator")
        safety_runtime = self._resolve_optional(self._safeties, safety, kind="safety") or self.default_safety_runtime
        memory_runtime = self._resolve_optional(self._memories, memory, kind="memory")
        self._validate_memory_runtime(memory_runtime)

        # 2. 为当前 agent 构造专属 ToolRuntime，只注入授权工具子集。
        tool_runtime = self._build_agent_tool_runtime(
            allowed_tools=list(allowed_tools or []),
            safety_runtime=safety_runtime,
        )

        # 3. 把解析后的依赖统一交给 AgentRuntime，再构造 Agent 实例。
        runtime = AgentRuntime(
            config=agent_config,
            model_name=model,
            engine_loop=engine_loop,
            model_runtime=model_runtime,
            safety_runtime=safety_runtime,
            tool_runtime=tool_runtime,
            retrieval_runtime=retrieval_runtime,
            memory_runtime=memory_runtime,
            evaluator_runtime=evaluator_runtime,
            observability_runtime=self.observability_runtime,
        )
        agent = agent_type(config=agent_config, runtime=runtime)
        setattr(agent, "name", name)
        return agent

    def _build_agent_tool_runtime(self, *, allowed_tools: list[str], safety_runtime: SafetyRuntime) -> ToolRuntime:
        """为当前 agent 构造专属工具运行时。"""

        tool_runtime = build_default_tool_runtime(
            safety_runtime=safety_runtime,
            observability_runtime=self.observability_runtime,
        )
        for tool_name in allowed_tools:
            registration = self._resolve_named(self._tools, tool_name, kind="tool")
            tool_runtime.register_tool(registration.spec, registration.handler)
        return tool_runtime

    def _normalize_tool(self, tool: Any) -> AgentAppTool:
        """把不同工具表达统一转换成 `AgentAppTool`。"""

        if isinstance(tool, AgentAppTool):
            return tool
        if (
            isinstance(tool, tuple)
            and len(tool) == 2
            and isinstance(tool[0], ToolSpec)
            and callable(tool[1])
        ):
            return AgentAppTool(spec=tool[0], handler=tool[1])

        spec = getattr(tool, "tool_spec", None)
        handler = getattr(tool, "execute", None)
        if isinstance(spec, ToolSpec) and callable(handler):
            return AgentAppTool(spec=spec, handler=handler)

        raise TypeError(
            "工具必须是 `AgentAppTool`、`(ToolSpec, handler)`，或者同时提供 `tool_spec` 与 `execute(...)` 的对象。"
        )

    def _validate_memory_runtime(self, runtime: Any | None) -> None:
        """校验 memory runtime 的最小契约。"""

        if runtime is None:
            return
        if not callable(getattr(runtime, "read", None)) or not callable(getattr(runtime, "write", None)):
            raise TypeError("memory runtime 必须同时提供 `read(...)` 和 `write(...)`。")

    def _resolve_named(self, registry: dict[str, Any], name: str, *, kind: str) -> Any:
        """解析一个必选注册项。"""

        if name not in registry:
            raise ValueError(f"未注册的{kind}: {name}")
        return registry[name]

    def _resolve_optional(self, registry: dict[str, Any], name: str | None, *, kind: str) -> Any | None:
        """解析一个可选注册项。"""

        if name is None:
            return None
        return self._resolve_named(registry, name, kind=kind)

    def _register_named(
        self,
        registry: dict[str, Any],
        name: str,
        value: Any,
        *,
        kind: str,
        allow_replace: bool = False,
    ) -> None:
        """向命名注册表写入一个对象。"""

        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{kind} 名称不能为空字符串。")
        normalized_name = name.strip()
        if normalized_name in registry and not allow_replace:
            raise ValueError(f"{kind} 已存在: {normalized_name}")
        registry[normalized_name] = value
