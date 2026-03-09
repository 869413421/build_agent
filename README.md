# 从 0 到 1 的劳动纠纷智能体

这是一个教程优先（tutorial-first）的仓库：目标是一步一步构建工程化 Agent 框架（`agent_forge`），并交付可实战的智能体应用。

## 你将实现什么

- 一个可复用的 Agent 框架（记忆、检索、上下文工程、智能体通信协议、智能体评估）
- 一个面向劳动者个人的劳动纠纷处理指导智能体
- 三种交付形态：CLI + HTTP API + Docker Compose

## 产品边界

- 本项目是法律信息辅助系统。
- 本项目不提供正式法律意见。
- 高风险情形应提示用户寻求法律援助或持证律师支持。

## 必读文件

- `docs/governance/NORTH_STAR.md`
- `docs/governance/AI_TASK_GUARDRAILS.md`
- `AGENTS.md`

## 教程路线图

完整 14 篇教程见 `docs/tutorials/`。

### 课程索引（按章节）

| 章节 | 主题 | 状态 | 链接 |
| --- | --- | --- | --- |
| 01 | 为什么你总是做不出可上线的 Agent | 已完成 | [第 01 章](docs/tutorials/01-从0到1工业级Agent框架打造-第一章-为什么你总是做不出可上线的Agent.md) |
| 02 | Protocol 协议层：手把手实战 | 已完成 | [第 02 章](docs/tutorials/02-从0到1工业级Agent框架打造-第二章-Protocol协议层-手把手实战.md) |
| 03 | Engine 循环：反思机制与生产约束 | 已完成 | [第 03 章](docs/tutorials/03-从0到1工业级Agent框架打造-第三章-Engine循环-反思机制与生产约束.md) |
| 04 | Model Runtime：大模型适配与防崩塌控制 | 已完成 | [第 04 章](docs/tutorials/04-从0到1工业级Agent框架打造-第四章-ModelRuntime-大模型适配与防崩塌控制.md) |
| 05 | Tool Runtime（API Adapter） | 已完成 | [第 05 章](docs/tutorials/05-从0到1工业级Agent框架打造-第五章-ToolRuntime-函数调用与隔离执行.md) |
| 06 | Observability | 已完成 | [第 06 章](docs/tutorials/06-从0到1工业级Agent框架打造-第六章-Observability-可观测与回放闭环.md) |
| 07 | Context Engineering | 已完成 | [第 07 章](docs/tutorials/07-从0到1工业级Agent框架打造-第七章-ContextEngineering-上下文编排与预算治理.md) |
| 08 | Retrieval | 已完成 | [第 08 章](docs/tutorials/08-从0到1工业级Agent框架打造-第八章-Retrieval-检索召回与引用标准化.md) |
| 09 | Memory | 已完成 | [第 09 章](docs/tutorials/09-从0到1工业级Agent框架打造-第九章-Memory-双层记忆写入与语义召回.md) |
| 10 | Evaluator | 已完成 | [第十章：Evaluator 结果评估与轨迹评分](docs/tutorials/10-从0到1工业级Agent框架打造-第十章-Evaluator-结果评估与轨迹评分.md) |
| 11 | Safety Layer | 已完成 | [第十一章：Safety Layer 输入、工具、输出三段防线](docs/tutorials/11-从0到1工业级Agent框架打造-第十一章-SafetyLayer-输入工具输出三段防线.md) |
| 12 | Agent 开箱即用入口与可扩展编排层 | 已完成 | [第十二章：Agent 开箱即用入口与可扩展编排层](docs/tutorials/12-从0到1工业级Agent框架打造-第十二章-Agent-开箱即用入口与可扩展编排层.md) |
| 13 | 生产发布与治理专题（预留） | 预留 | 待发布 |
| 14 | 生产发布与治理专题（预留） | 预留 | 待发布 |

## 快速开始

1. 安装依赖：

```bash
uv sync --dev
```

2. 主推荐入口运行 `AgentApp()`：

```bash
uv run python -c "import asyncio; from agent_forge import AgentApp; app = AgentApp(); agent = app.create_agent(name='researcher', model='default'); result = asyncio.run(agent.arun('帮我梳理一下任务下一步')); print(result.summary)"
```

3. 轻量直用路径运行 `Agent()`：

```bash
uv run python -c "import asyncio; from agent_forge import Agent; result = asyncio.run(Agent().arun('帮我梳理一下任务下一步')); print(result.summary)"
```

4. 查看 CLI 版本入口：

```bash
uv run agent-forge version
```

5. 启动 API 健康检查：

```bash
uv run python -m uvicorn agent_forge.apps.api.app:app --reload
```

6. 访问健康检查：

```bash
curl http://127.0.0.1:8000/v1/health
```
