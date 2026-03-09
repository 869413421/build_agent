# 教程与代码对齐审计

## 目标

本文件用于记录当前教程与主线代码的一致性状态，作为公开发布教程前的准入基线。

## 当前结论

截至 2026-03-09，教程体系暂不满足“可直接公开面向读者使用”的标准。

原因不是单一章节瑕疵，而是主入口层在近期连续发生了真实契约收口：

1. `AgentApp` 成为主推荐入口。
2. `Agent / AgentRuntime` 的注释、错误文案与主流程注释已重写。
3. `allowed_tools` 与 `memory` 已接通主链路。
4. `ToolRuntime` 的并发与幂等语义已经收紧。
5. README 目前仍存在明显编码污染。

这些变化会直接影响教程中的：

1. 顶层 API 用法。
2. 示例代码。
3. 文件代码块。
4. 架构图与章节承接。
5. Quickstart 命令与预期输出。

## 已确认的阻塞项

### 1. 第 12 章已确认代码漂移

执行结果：

```bash
uv run python .agents/skills/tutorial-quality-checker/scripts/check_tutorial_markers.py --file "docs/tutorials/12-从0到1工业级Agent框架打造-第十二章-Agent-开箱即用入口与可扩展编排层.md"
```

结论：`FAIL`

已确认漂移文件：

1. [src/agent_forge/runtime/__init__.py](D:/code/build_agent/src/agent_forge/runtime/__init__.py)
2. [src/agent_forge/__init__.py](D:/code/build_agent/src/agent_forge/__init__.py)
3. [src/agent_forge/runtime/schemas.py](D:/code/build_agent/src/agent_forge/runtime/schemas.py)
4. [src/agent_forge/runtime/defaults.py](D:/code/build_agent/src/agent_forge/runtime/defaults.py)
5. [src/agent_forge/runtime/runtime.py](D:/code/build_agent/src/agent_forge/runtime/runtime.py)
6. [src/agent_forge/runtime/agent.py](D:/code/build_agent/src/agent_forge/runtime/agent.py)
7. [examples/agent/agent_demo.py](D:/code/build_agent/examples/agent/agent_demo.py)

这说明第 12 章不能直接公开。

### 2. README 当前不适合直接作为公开入口

当前 [README.md](D:/code/build_agent/README.md) 存在明显中文乱码，且其中的主入口叙事仍未完全对齐现在的 `AgentApp -> Agent -> AgentRuntime` 真实结构。

这意味着：

1. 公开仓库首页会直接误导读者。
2. Quickstart 体验不可信。
3. 后续章节索引也会被污染。

### 3. 01-11 章需要做继承式回收

虽然目前只正式跑了第 12 章检查，但从主入口与组件边界变更幅度看，01-11 章至少需要做一轮“接口引用、章节承接、命令与入口命名”的回收。

风险最高的章节：

1. 第 5 章 `ToolRuntime`
2. 第 6 章 `Observability`
3. 第 9 章 `Memory`
4. 第 11 章 `Safety`
5. 第 12 章 `Agent`

## 当前发布判断

### 教程是否可公开

结论：`否`

只有同时满足这些条件后，才允许公开：

1. `README.md` 无编码污染。
2. 第 12 章 `tutorial-quality-checker` 与 `run_article_checks.py` 均通过。
3. 01-12 全部章节完成一轮代码漂移复核。
4. README Quickstart 与当前真实代码一致。

## 后续处理顺序

1. 先修 `README.md`。
2. 再重写第 12 章，使其以 `AgentApp` 为主入口。
3. 回收第 5/6/9/11 章的接口叙事。
4. 最后统一复核 01-12 全部章节。
