# 《从0到1工业级Agent框架打造》第一章：你的Agent为什么永远停在Demo阶段？
## 这套课到底会学什么（课程全景）

很多教程的问题是：单章讲得热闹，但你不知道整条路线怎么走。  
这套课从第一章开始就把地图摊开，避免你学到一半发现方向不对。

14 章的主线分成四段：

1. 打地基（第 1-4 章）：骨架、协议、执行引擎、模型运行时。  
2. 长能力（第 5-8 章）：工具运行时、可观测、上下文工程、检索。  
3. 稳系统（第 9-11 章）：记忆、评测、安全层。  
4. 可交付（第 12-14 章）：API/CLI 集成、部署与质量门禁。

你可以把它理解成一条固定节奏：  
先把系统“跑起来”，再让系统“做得对”，最后让系统“敢上线”。

## 学完后你能拿到什么（阶段展望）

这不是“看完很懂，开工还不会”的那种课程。  
按章节跟下来，你会拿到三层可交付产物：

1. 工程层：一套可运行、可测试、可扩展的 `agent_forge` 框架骨架。  
2. 架构层：从 Protocol 到 Safety 的完整组件链路与边界约束。  
3. 交付层：可演示、可回归、可持续迭代的项目工程（不是一次性 Demo）。

换句话说，最后你交出去的不是“一个聪明回答”，而是一套“可维护系统”。

## 你适不适合这套课（先判断，再投入）

适合你，如果你满足下面任意两条：

1. 做过后端或平台开发，想把 Agent 做成“可上线系统”，不是一次性 Demo。
2. 遇到过“Demo 很惊艳、线上难排查”的问题，想补齐工程基本盘。
3. 希望沉淀一套可复用框架，而不是只完成一个项目。

不太适合你，如果你当前目标是：

1. 只想快速出一个演示，不关心长期维护。
2. 只关心 Prompt 结果，不打算做测试、回归和版本治理。
3. 不接受“先打地基、后堆能力”的学习节奏。

## 学这套课需要哪些知识点

必备：

1. Python 基础：函数、模块、包导入、虚拟环境。
2. 命令行基础：能执行 `uv`、`pytest`、基本文件操作。
3. Web 基础：理解 HTTP 路由与 JSON 返回。

加分项（不会也能跟）：

1. `asyncio` 基础认知。
2. `typing` 与 `pydantic` 基础用法。
3. 对测试、lint、发布流程有基本概念。

如果你现在只具备“必备项”，可以直接开学。  
因为本系列每章都坚持：完整代码 + 可运行命令 + 可验证结果。

## 本章目标

1. 捅破 Agent 项目从 Demo 到上线之间那层最常见的“窗户纸”。
2. 搭起一个最小可运行骨架（CLI + API + 测试），这是后面14章的起跑线。
3. 定个规矩：后面每章，必须有代码、有测试、能验证。咱们不搞“脑补架构”。

## 架构位置说明（演进视角）

### 当前系统结构（第 1 章起点）

```mermaid
flowchart TD
  A[CLI 入口] --> B[API 入口]
```

### 本章完成后的结构

```mermaid
flowchart TD
  A[CLI 入口] --> B[API 入口]
  B --> C[测试护栏与回归入口]
```

本章定位很明确：先把工程外壳和验证护栏立住。

1. 新增模块依赖关系：测试依赖 `src` 主线代码，不引入反向依赖。
2. 依赖方向保持稳定：应用入口 -> 组件代码 -> 测试验证。
3. 本章不引入循环依赖，后续章节只做增量扩展，不推翻现有骨架。

---

## 深入理解：为什么第一章先抓“骨架”而不是“能力”

### 一句话先讲人话

第一章不是在教你“写一个能跑的脚本”，而是在教你避免“演示能跑、上线就崩”的架构陷阱。

### 真实例子

成功链路例子：

1. 先把协议、执行、模型、工具拆层。
2. 每层只暴露稳定接口。
3. 任一层替换实现时，上层不需要重写。

失败链路例子：

1. 把模型调用、工具调用、状态更新都写在一个大函数里。
2. 一处改参数会牵连全局。
3. 调试时只能“整段打印日志”，无法定位具体故障点。

### 为什么“分层 + 小步”能救命

```mermaid
flowchart TD
  A[需求变化] --> B{是否分层}
  B -->|是| C[只改局部组件]
  B -->|否| D[全链路联动修改]
  C --> E[风险可控]
  D --> F[回归成本爆炸]
```

### 读这一章时的抓手

1. 不要纠结术语，先抓“为什么之前总做成一次性 demo”。
2. 看到每个规范时，问自己：它是在防哪一种线上事故。
3. 记住核心目标：不是快，而是可持续迭代。

## 动手之前

1. Python 版本 >= 3.11
2. 装好 `uv`
3. 所有命令都在仓库根目录执行

## 环境准备（复制粘贴即可）

```bash
uv init
uv add fastapi typer pydantic pydantic-settings python-dotenv openai
uv add --dev pytest
uv sync --dev
```

## 代码放在哪

- 主线演进目录：`src/agent_forge/`

## 本章主线改动范围（强制声明）

### 代码目录

- `src/agent_forge/apps/`

### 测试目录

- `tests/`

### 本章涉及的真实文件

- [pyproject.toml](../../pyproject.toml)
- [src/agent_forge/apps/cli.py](../../src/agent_forge/apps/cli.py)
- [src/agent_forge/apps/api/app.py](../../src/agent_forge/apps/api/app.py)
- [tests/conftest.py](../../tests/conftest.py)
- [tests/unit/test_bootstrap.py](../../tests/unit/test_bootstrap.py)

约束说明：本章只做主线增量，不引入占位文件，不添加“下章再删”的过渡代码。

## 开干

### 第 1 步：先聊点实际的

做过 Agent 的，下面这场景熟不熟？

- **第 1 天**：调了两句 Prompt，效果惊艳，感觉马上要起飞。
- **第 7 天**：接上工具、状态和接口，开始时不时抽风一下。
- **第 30 天**：问题在哪都搞不清楚，团队里开始有人嘀咕“要不重写吧”。

真不是模型不行，是工程底子没打好。

所以第一章我们不讲花哨能力，只干一件事：把**最小可运行骨架**立起来，并且让测试能给出确定反馈。

```mermaid
flowchart TD
  A[创建工程骨架] --> B[补齐 CLI 与 API 最小入口]
  B --> C[写 bootstrap 单测]
  C --> D[运行 pytest 验证]
  D --> E[主线一致性检查]
```

### 第 2 步：创建目录和文件

```bash
mkdir -p src/agent_forge/apps/api
mkdir -p tests/unit
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force src/agent_forge/apps/api | Out-Null
New-Item -ItemType Directory -Force tests/unit | Out-Null
```

### 第 3 步：写核心代码

创建命令：

```bash
touch pyproject.toml
```

```powershell
New-Item -ItemType File -Force "pyproject.toml" | Out-Null
```

**文件：** `pyproject.toml`

```toml
[project]
name = "agent-forge-chapter-01"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115.0",
  "typer>=0.12.0",
  "pytest>=8.3.0",
]

[project.scripts]
agent-forge = "agent_forge.apps.cli:app"
```

代码讲解（`pyproject.toml`）：

1. 主流程拆解
2. `name/version/requires-python` 锁定工程身份与运行边界，保证团队机器和 CI 的解释器语义一致。
3. `dependencies` 把“能跑起来最小集合”一次性写清，避免后续章节出现“我本地能跑，你那边不行”的幽灵问题。
4. `[project.scripts]` 把 `agent-forge` 映射到 `agent_forge.apps.cli:app`，形成统一入口，后续所有 CLI 子命令都挂在这个门面上。

成功链路例子：

1. 新同学拉仓库后执行 `uv sync --dev`。
2. 入口脚本生成成功。
3. `uv run agent-forge version` 输出版本字符串，主线连通。

失败链路例子：

1. 忘了写 `[project.scripts]`。
2. 测试可能仍能通过（因为直接 import 函数），但 CLI 无法被系统识别。
3. 到联调阶段才暴露“命令不存在”，返工成本更高。

```mermaid
flowchart TD
  A[pyproject.toml] --> B[uv sync --dev]
  B --> C[生成命令入口 agent-forge]
  C --> D[CLI 子命令可执行]
```

工程取舍与边界：

1. 第一章只保留最小依赖，不提前引入重量库，目的是让读者先建立稳定主线。
2. 这里暂不锁死精确 patch 版本，是为了降低课程初期安装摩擦；进入生产发布阶段再补充锁版本策略。

创建命令：

```bash
touch src/agent_forge/apps/cli.py
```

```powershell
New-Item -ItemType File -Force "src\agent_forge\apps\cli.py" | Out-Null
```

**文件：** `src/agent_forge/apps/cli.py`

```python
"""CLI entry for 主线 01."""

from __future__ import annotations

import typer

app = typer.Typer(help="agent_forge 主线 01 CLI")


@app.callback()
def main() -> None:
    """CLI root command group."""


@app.command()
def version() -> None:
    """Print 主线 bootstrap version."""

    typer.echo("agent-forge-chapter-01")


if __name__ == "__main__":
    app()
```

这个文件看起来简单，但它非常关键：这是后续所有 CLI 能力的门面入口。

代码讲解（`cli.py`）：

1. 主流程拆解
2. `app = typer.Typer(...)` 创建命令组容器，是 CLI 的“路由总线”。
3. `@app.callback()` 强制启用“子命令模式”，避免 Typer 退化成单命令语义。
4. `@app.command()` 注册 `version`，将“可观测的最小输出”挂到统一入口上。

成功链路例子：

1. 命令 `uv run agent-forge version` 进入 `main()` -> 路由到 `version()`。
2. 控制台输出 `agent-forge-chapter-01`，说明入口、命令路由、执行函数全部打通。

失败链路例子：

1. 去掉 `@app.callback()` 且只保留一个命令。
2. Typer 可能把 `version` 当主命令，导致 `agent-forge version` 报 `Got unexpected extra argument (version)`。
3. 这类问题常在“命令看起来都写了”时出现，最容易误判为环境问题。

```mermaid
sequenceDiagram
  participant U as User
  participant E as Command Entry
  participant T as Typer app
  participant V as Version Command
  U->>E: agent-forge version
  E->>T: load app
  T->>V: dispatch subcommand
  V-->>U: agent-forge-chapter-01
```

工程取舍与边界：

1. 第一章不接入复杂 CLI 参数，是为了把入口语义先固定，再逐章扩展能力。
2. `version()` 用固定字符串而非动态读取包元数据，减少初期依赖链复杂度，后续章节再升级为统一版本源。

创建命令：

```bash
touch src/agent_forge/apps/api/app.py
```

```powershell
New-Item -ItemType File -Force "src\agent_forge\apps\api\app.py" | Out-Null
```

**文件：** `src/agent_forge/apps/api/app.py`

```python
"""FastAPI app for 主线 01."""

from fastapi import FastAPI

app = FastAPI(title="agent_forge_chapter_01")


@app.get("/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

代码讲解（`api/app.py`）：

1. 主流程拆解
2. `FastAPI(...)` 创建 HTTP 应用实例，承载后续所有 API 路由。
3. `@app.get("/v1/health")` 建立健康探针，给部署与监控系统一个稳定检查点。
4. `health()` 返回结构化字典，确保测试、运维探针、网关都能用一致格式判断服务状态。

成功链路例子：

1. 应用启动后访问 `/v1/health` 返回 `{"status": "ok"}`。
2. 测试直接调用 `health()` 也返回同样结构，API 行为与单测断言保持一致。

失败链路例子：

1. 返回值改成字符串 `"ok"`。
2. 人工看似没问题，但自动化断言或网关 JSON 规则可能失败。
3. 线上健康检查误判为异常，导致实例被频繁摘除。

```mermaid
flowchart LR
  A[Probe Or Test] --> B[Health Endpoint]
  B --> C[Status OK]
  C --> D[Service Healthy]
```

工程取舍与边界：

1. 第一章只提供只读健康检查，不引入写操作，避免还没建好安全边界就暴露副作用接口。
2. 先固定 `/v1` 前缀，是为后续版本演进预留路径空间。

### 第 4 步：写测试

创建命令：

```bash
touch tests/conftest.py
```

```powershell
New-Item -ItemType File -Force "tests\conftest.py" | Out-Null
```

**文件：** `tests/conftest.py`

```python
"""Test bootstrap for 主线 01 snapshot."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
```

创建命令：

```bash
touch tests/unit/test_bootstrap.py
```

```powershell
New-Item -ItemType File -Force "tests\unit\test_bootstrap.py" | Out-Null
```

**文件：** `tests/unit/test_bootstrap.py`

```python
"""主线 01 bootstrap tests."""

from __future__ import annotations

from agent_forge.apps.api.app import health


def test_health_endpoint_function() -> None:
    assert health() == {"status": "ok"}
```

代码讲解（`tests/conftest.py` + `tests/unit/test_bootstrap.py`）：

1. 主流程拆解
2. `conftest.py` 在测试启动时把 `src/` 注入 `sys.path`，让测试运行环境与仓库源码目录对齐。
3. `test_bootstrap.py` 直接断言 `health()` 输出，验证“最小 API 语义”是否成立。
4. 两者组合形成第一条回归护栏：环境可导入 + 核心行为可断言。

成功链路例子：

1. 执行 `uv run pytest tests/unit/test_bootstrap.py -q`。
2. `agent_forge` 可导入，断言命中，回归通过。

失败链路例子：

1. 删除或写错 `conftest.py` 路径注入。
2. 立刻出现 `ModuleNotFoundError`，在第一章就能暴露而不是拖到后续复杂章节。

```mermaid
flowchart TD
  A[pytest 启动] --> B[加载 conftest 注入 src 路径]
  B --> C[导入 agent_forge.apps.api.app]
  C --> D[执行 health 断言]
  D --> E[通过或失败]
```

工程取舍与边界：

1. 这里选择“函数级验证”而非端到端 HTTP 测试，是为了降低第一章认知负担，先把最小可验证链路建立起来。
2. 当路由、依赖注入、鉴权中间件增多后，再逐章补充 TestClient 与集成测试。

### 第 5 步：一致性检查

这一节只做两件事：

1. 确认本章文件都已经落在主线路径（`src/`、`tests/`）。
2. 确认入口命令与测试命令都可直接运行。

Bash：

```bash
ls src/agent_forge/apps
ls tests/unit
```

Windows PowerShell：

```powershell
Get-ChildItem src/agent_forge/apps
Get-ChildItem tests/unit
```

## 运行命令

验证主线：

```bash
uv run pytest tests/unit/test_bootstrap.py -q
```

验证主线工程：

```bash
uv pip install -e .
uv run agent-forge version
# 预期输出: agent-forge-chapter-01
```


PowerShell 等价命令：

```powershell
uv run pytest tests/unit/test_bootstrap.py -q
uv pip install -e .
uv run agent-forge version
```

## 环境准备与缺包兜底步骤（可直接复制）

当你在公司网络、离线环境或本地权限受限时，优先按下面顺序排查：

```bash
uv --version
python --version
uv sync --dev
uv run pytest tests/unit/test_bootstrap.py -q
```

Windows PowerShell：

```powershell
uv --version
python --version
uv sync --dev
uv run pytest tests/unit/test_bootstrap.py -q
```

若 `uv sync --dev` 因缓存权限或网络策略失败，可临时使用 Python 兜底验证“第一章主线是否可跑”：

```bash
python -m pytest tests/unit/test_bootstrap.py -q
python -m agent_forge.apps.cli version
```

```powershell
python -m pytest tests/unit/test_bootstrap.py -q
python -m agent_forge.apps.cli version
```

这一步的设计意图是先确认“代码主线没问题”，再回头治理 `uv` 环境问题，避免把业务故障和环境故障混在一起排查。

## 增量闭环验证

1. 主程序可运行：`agent-forge version` 能稳定返回版本字符串。
2. 新增能力可见：`/v1/health` 与 `test_bootstrap` 同时通过。
3. 回归不破坏：后续章节在此骨架上扩展，不需要回头重写第一章代码。

## 检查清单

1. 本章测试能跑通。
2. `agent-forge version` 能执行并输出版本号。
3. 教程中的路径和仓库真实文件一致。

## 翻车了怎么办？

**翻车现场 1：`ModuleNotFoundError: No module named 'agent_forge'`**

检查 `tests/conftest.py` 是否存在并且路径注入正确。

**翻车现场 2：`agent-forge: command not found`**

检查 `pyproject.toml` 里的 `[project.scripts]`，并重新执行 `uv sync --dev`。

**翻车现场 3：`Got unexpected extra argument (version)`**

这是 Typer 的单命令模式问题。若只有一个 `@app.command()`，Typer 会把它当主命令而不是子命令。  
本章已通过 `@app.callback()` 强制多子命令模式，确保 `agent-forge version` 可用。
如果你本地仍报这个错误，通常是入口脚本还没刷新，执行下面命令后重试：

```bash
uv sync --dev
uv run agent-forge version
```

## 本章完成标志（DoD）

1. 能从空目录搭出可运行骨架。
2. 能跑通第一条自动化测试。
3. `agent-forge version` 可执行。

## 下一章预告

下一章进入 `Protocol` 组件：统一消息、状态和错误契约，让组件之间真正“说同一种语言”。
