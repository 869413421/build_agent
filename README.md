# 从 0 到 1 的工业级 Agent 框架实战仓库

这是一个教程优先、单工程连续演进的 Agent 框架仓库。

仓库主线目标有两条：

1. 逐步实现一个可扩展的 `agent_forge` 框架。
2. 基于同一套框架，继续落地真实应用入口与交付层。

当前仓库已经完成 01-12 章对应的主干能力实现，包括：

1. Protocol
2. Engine
3. Model Runtime
4. Tool Runtime
5. Observability
6. Context Engineering
7. Retrieval
8. Memory
9. Evaluator
10. Safety Layer
11. AgentRuntime
12. AgentApp / Agent 主入口

## 当前状态

当前代码状态：

1. 框架主线可运行。
2. 全量回归通过。
3. `AgentApp -> Agent -> AgentRuntime -> EngineLoop` 主链路已成形。

当前发布状态：

1. 仍处于 `alpha / 内部验证中`。
2. 暂不承诺 `production-ready`。
3. 教程体系仍在做统一对齐，不建议直接对外公开使用。

详见：

- [PROJECT_STATUS.md](D:/code/build_agent/docs/governance/PROJECT_STATUS.md)
- [TUTORIAL_ALIGNMENT_AUDIT.md](D:/code/build_agent/docs/governance/TUTORIAL_ALIGNMENT_AUDIT.md)
- [PRODUCTION_READINESS_CHECKLIST.md](D:/code/build_agent/docs/governance/PRODUCTION_READINESS_CHECKLIST.md)

## 快速开始

### 1. 安装依赖

```bash
uv sync --dev
```

```powershell
uv sync --dev
```

### 2. 主推荐入口：`AgentApp`

```python
import asyncio

from agent_forge import AgentApp


async def main() -> None:
    app = AgentApp()
    agent = app.create_agent(
        name="researcher",
        model="default",
    )
    result = await agent.arun("帮我总结一下这个主题的下一步行动建议")
    print(result.summary)
    print(result.output)


asyncio.run(main())
```

### 3. 轻量直用入口：`Agent`

```python
import asyncio

from agent_forge import Agent


async def main() -> None:
    agent = Agent()
    result = await agent.arun("帮我总结一下这个主题的下一步行动建议")
    print(result.summary)


asyncio.run(main())
```

### 4. 运行示例

```bash
uv run --no-sync python examples/agent/agent_app_demo.py
uv run --no-sync python examples/agent/agent_demo.py
```

```powershell
uv run --no-sync python examples/agent/agent_app_demo.py
uv run --no-sync python examples/agent/agent_demo.py
```

### 5. 运行测试

```bash
uv run --no-sync pytest -q
```

```powershell
uv run --no-sync pytest -q
```

## 推荐阅读顺序

### 治理与约束

- [NORTH_STAR.md](D:/code/build_agent/docs/governance/NORTH_STAR.md)
- [AI_TASK_GUARDRAILS.md](D:/code/build_agent/docs/governance/AI_TASK_GUARDRAILS.md)
- [AGENTS.md](D:/code/build_agent/AGENTS.md)

### 架构接口

- [interfaces.md](D:/code/build_agent/docs/architecture/interfaces.md)

### 教程章节

1. [第一章](D:/code/build_agent/docs/tutorials/01-从0到1工业级Agent框架打造-第一章-为什么你总是做不出可上线的Agent.md)
2. [第二章](D:/code/build_agent/docs/tutorials/02-从0到1工业级Agent框架打造-第二章-Protocol协议层-手把手实战.md)
3. [第三章](D:/code/build_agent/docs/tutorials/03-从0到1工业级Agent框架打造-第三章-Engine循环-反思机制与生产约束.md)
4. [第四章](D:/code/build_agent/docs/tutorials/04-从0到1工业级Agent框架打造-第四章-ModelRuntime-大模型适配与防崩塌控制.md)
5. [第五章](D:/code/build_agent/docs/tutorials/05-从0到1工业级Agent框架打造-第五章-ToolRuntime-函数调用与隔离执行.md)
6. [第六章](D:/code/build_agent/docs/tutorials/06-从0到1工业级Agent框架打造-第六章-Observability-可观测与回放闭环.md)
7. [第七章](D:/code/build_agent/docs/tutorials/07-从0到1工业级Agent框架打造-第七章-ContextEngineering-上下文编排与预算治理.md)
8. [第八章](D:/code/build_agent/docs/tutorials/08-从0到1工业级Agent框架打造-第八章-Retrieval-检索召回与引用标准化.md)
9. [第九章](D:/code/build_agent/docs/tutorials/09-从0到1工业级Agent框架打造-第九章-Memory-双层记忆写入与语义召回.md)
10. [第十章](D:/code/build_agent/docs/tutorials/10-从0到1工业级Agent框架打造-第十章-Evaluator-结果评估与轨迹评分.md)
11. [第十一章](D:/code/build_agent/docs/tutorials/11-从0到1工业级Agent框架打造-第十一章-SafetyLayer-输入工具输出三段防线.md)
12. [第十二章](D:/code/build_agent/docs/tutorials/12-从0到1工业级Agent框架打造-第十二章-Agent-开箱即用入口与可扩展编排层.md)

## 框架主入口

### `AgentApp`

推荐在应用层使用：

1. 注册共享能力。
2. 按名字装配 agent。
3. 统一作为 CLI / API 的装配入口。

### `Agent`

推荐在两类场景使用：

1. 轻量直用。
2. 通过继承扩展 `_before_run / _after_run / _get_context / _get_capabilities` 等钩子。

### `AgentRuntime`

这是内部编排层，负责统一串联：

1. input safety
2. memory read
3. retrieval
4. engine loop
5. tool runtime
6. output safety
7. evaluator
8. memory write

## 当前不建议对外承诺的内容

以下内容仍未完成，不建议对外宣传为“已生产可用”：

1. 正式 CLI 业务入口
2. 正式 HTTP API 执行入口
3. preflight 配置门禁
4. Docker Compose 交付闭环
5. 压测、故障注入、运维交接

## 维护说明

如果你当前要继续推进这个仓库，建议先做两件事：

1. 统一同步 `README + interfaces + docs/tutorials/01-12`
2. 再进入 CLI / API / 部署层开发
