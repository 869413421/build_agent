# 从 0 到 1 的劳动纠纷智能体

这是一个教程优先（tutorial-first）的仓库：目标是一步一步构建工程化 Agent 框架，并交付一个可实战使用的劳动纠纷处理指导智能体。

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

## 快速开始

1. 安装依赖：

```bash
pip install -e .[dev]
```

2. 启动 API：

```bash
labor-agent serve
```

3. 测试健康检查：

```bash
curl http://127.0.0.1:8000/v1/health
```

4. 终端快速体验案情采集：

```bash
labor-agent intake "公司拖欠我两个月工资并拒绝补发"
```
