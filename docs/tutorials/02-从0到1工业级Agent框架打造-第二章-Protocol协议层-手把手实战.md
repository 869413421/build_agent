# 《从0到1工业级Agent框架打造》第二章：先把“共同语言”焊死，系统才不会边跑边散架

## 目标

1. 搭建 Protocol 组件的完整对象模型：`AgentMessage`、`ToolCall`、`ToolResult`、`ExecutionEvent`、`FinalAnswer`、`AgentState`。
2. 建立“协议先行”的工程纪律：新能力先对齐协议，再写实现。
3. 交付可独立运行的主线（代码 + 测试），并与主线 `src/agent_forge` 保持一致。

## 如果你第一次接触 Protocol，先记这 3 句话

1. Protocol 不是注释文档，而是整个 Agent 系统的公共语言层。
2. 这层的价值，不在于“字段写得全”，而在于“后面所有组件都按同一种结构说话”。
3. 如果这一层没焊死，后面的 Engine、Model Runtime、Tool Runtime 都会出现字段漂移和状态漂移。

第一次读这一章时，先不要试图记住所有 schema 细节。先抓住一句话：

`Protocol` 负责规定“什么数据可以进入主链路，以及进入后该长什么样”。 

## 架构位置说明（演进视角）

### 当前系统结构（第 2 章开始前）

```mermaid
flowchart TD
  A[CLI/API 入口] --> B[Engine 预留位置]
  B --> C[待统一的数据契约]
```

### 本章完成后的结构

```mermaid
flowchart TD
  A[CLI/API 入口] --> B[Protocol 契约层]
  B --> C[Engine/Model/Tool 组件]
  B --> D[测试与回归]
```

1. 新模块依赖谁：Protocol 仅依赖基础库（pydantic），不反向依赖 Engine。
2. 谁依赖它：后续 Engine、Model Runtime、Tool Runtime 都以它为统一输入输出契约。
3. 依赖方向是否变化：变化为“先协议后实现”，降低跨组件耦合。
4. 循环风险：本章保持单向依赖，不引入循环依赖。

## 名词速览

第一次读 Protocol，最容易混的不是代码，而是这些词到底各自站在链路的哪一层：

1. `Protocol`：全链路共享的数据契约，不是“文档说明”，而是会被代码和测试直接执行的边界。
2. `Schema`：协议里的具体对象定义，比如 `ToolCall`、`ToolResult`、`AgentState`。
3. `Contract`：工程语义上的“约定”，强调上下游都必须遵守，不是“尽量如此”。
4. `Validation`：进入主链路前的结构校验，核心作用是把脏数据挡在边界外。
5. `AgentState`：运行时单一事实源，后续 Engine 的 plan/act/observe/reflect 都围绕它读写。
6. `ExecutionEvent`：给可观测、回放、评测消费的事件记录，不是业务结果本身。
7. `FinalAnswer`：面向最终输出的稳定结构，服务前端展示、评测和审计。
8. `protocol_version`：协议版本号，解决的不是“好不好看”，而是“未来改字段时能不能定位兼容性问题”。

> Protocol 不是“把字段写全”，而是“把系统以后会互相甩锅的地方，提前焊死成统一边界”。

## 前置条件

1. Python >= 3.11
2. 已安装 `uv`
3. 当前命令执行目录：仓库根目录（即包含 `src/`、`tests/`、`docs/` 的目录）
4. 已完成第一章（你已经有最小 CLI/API 骨架）

## 环境准备

```bash
uv add pydantic
uv add --dev pytest
uv sync --dev
```

环境准备与缺包兜底（可直接复制）：

```bash
uv run pytest tests/unit/test_protocol.py -q
```

```powershell
uv run pytest tests/unit/test_protocol.py -q
```

若 `uv` 在当前机器因缓存权限失败，可先验证主线逻辑是否正确：

```bash
python -m pytest tests/unit/test_protocol.py -q
```

```powershell
python -m pytest tests/unit/test_protocol.py -q
```

## 先讲“面”：为什么第二章必须先做 Protocol

第一章我们解决的是“项目能启动”。  
第二章要解决的是“项目能协作”。

没有统一协议时，工程会出现三个典型症状：

1. 字段漂移：模型这周返回 `answer`，下周返回 `result`，到处写兜底 `if/else`。
2. 状态漂移：Engine、Runtime、日志系统各存一份状态，出了问题没人知道哪份是真的。
3. 错误漂移：错误只是一段字符串，系统不知道是该重试、降级还是立刻失败。

Protocol 的价值，就是把这些漂移变成“结构化、可校验、可演进”的确定性边界。

```mermaid
flowchart TD
  A[用户输入] --> B[AgentMessage]
  B --> C[AgentState]
  C --> D[Engine Loop]
  D --> E[ToolCall]
  E --> F[ToolResult]
  D --> G[ExecutionEvent]
  D --> H[FinalAnswer]
  F --> C
  G --> C
  H --> C
```

这条链路你可以先记一句话：  
所有输入输出，**都先落到协议对象**，再被各组件消费。

## 深入理解：Protocol 为什么是全链路的“同一种语言”

### 白话理解 Protocol

Protocol 就是“团队约定的统一表格”。

- 你填什么字段，我就按什么字段处理。
- 没有这张表，大家都在猜字段含义，系统必然越来越乱。

### 例子：同一个 Tool 调用，为什么要标准化

成功链路例子：

1. 模型产出 `tool_call_id/tool_name/args`。
2. Tool Runtime 按固定结构执行并返回 `ToolResult`。
3. Engine 只认 `status/output/error`，无需猜测。

失败链路例子：

1. 某工具返回 `{"ok": true}`，另一个返回 `{"success": 1}`。
2. Engine 里写满 if/else 兼容判断。
3. 新增第三个工具后继续膨胀，最终不可维护。

### 协议统一后数据怎么流

```mermaid
flowchart LR
  A[Model/Planner] --> B[ToolCall]
  B --> C[Tool Runtime]
  C --> D[ToolResult]
  D --> E[Engine]
```

再看得更工程一点，Protocol 实际上在做三层约束：

```mermaid
flowchart TD
  A[上游产生结构] --> B[Schema 校验]
  B --> C[进入主链路]
  C --> D[写入 State 或 Event]
  D --> E[被下游组件消费]
```

1. 上游可以来自模型、工具、用户输入或内部运行时。
2. 只要要进入主链路，就先过 Schema 校验。
3. 通过校验后，数据才有资格进入 `AgentState` 或 `ExecutionEvent`。
4. 下游组件消费的是“被收口后的结构”，而不是原始野数据。

### 实战读法

1. 看字段时重点看“谁生产、谁消费、谁校验”。
2. 关注 `error_code/retryable` 这种“执行决策字段”，不是装饰字段。
3. 把协议当成“防回归边界”，不是文档摆设。

## 本章主线改动范围

### 代码目录

- `src/agent_forge/components/protocol/`

### 测试目录

- `tests/unit/`

### 本章涉及的真实文件

- [src/agent_forge/components/protocol/__init__.py](../../src/agent_forge/components/protocol/__init__.py)
- [src/agent_forge/components/protocol/domain/__init__.py](../../src/agent_forge/components/protocol/domain/__init__.py)
- [src/agent_forge/components/protocol/domain/schemas.py](../../src/agent_forge/components/protocol/domain/schemas.py)
- [tests/unit/test_protocol.py](../../tests/unit/test_protocol.py)

约束说明：本章只新增协议层能力，不引入临时代码，不推翻第一章骨架。

## 再讲“点”：本章具体实施步骤

### 第 1 步：创建目录

```bash
mkdir -p src/agent_forge/components/protocol/domain
mkdir -p tests/unit
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force src/agent_forge/components/protocol/domain | Out-Null
New-Item -ItemType Directory -Force tests/unit | Out-Null
```

### 第 2 步：写 Protocol 导出入口

创建命令：

```bash
touch src/agent_forge/components/protocol/__init__.py
```

```powershell
New-Item -ItemType File -Force "src\\agent_forge\\components\\protocol\\__init__.py" | Out-Null
```
文件：[src/agent_forge/components/protocol/__init__.py](../../src/agent_forge/components/protocol/__init__.py)

```python
"""Protocol component exports."""

from agent_forge.components.protocol.domain.schemas import (
    PROTOCOL_VERSION,
    AgentMessage,
    AgentState,
    ErrorInfo,
    ExecutionEvent,
    FinalAnswer,
    ToolCall,
    ToolResult,
    build_initial_state,
)

__all__ = [
    "PROTOCOL_VERSION",
    "AgentMessage",
    "AgentState",
    "ErrorInfo",
    "ExecutionEvent",
    "FinalAnswer",
    "ToolCall",
    "ToolResult",
    "build_initial_state",
]
```

创建命令：

```bash
touch src/agent_forge/components/protocol/domain/__init__.py
```

```powershell
New-Item -ItemType File -Force "src\\agent_forge\\components\\protocol\\domain\\__init__.py" | Out-Null
```
文件：[src/agent_forge/components/protocol/domain/__init__.py](../../src/agent_forge/components/protocol/domain/__init__.py)

```python
﻿"""Protocol domain exports."""

from .schemas import (
    PROTOCOL_VERSION,
    AgentMessage,
    AgentState,
    ErrorInfo,
    ExecutionEvent,
    FinalAnswer,
    ToolCall,
    ToolResult,
    build_initial_state,
)

__all__ = [
    "PROTOCOL_VERSION",
    "AgentMessage",
    "AgentState",
    "ErrorInfo",
    "ExecutionEvent",
    "FinalAnswer",
    "ToolCall",
    "ToolResult",
    "build_initial_state",
]

```

代码讲解：

1. 设计动机：把组件的公开 API 收敛在一个入口，外部不直接依赖内部目录细节。
2. 工程取舍：使用 `__all__` 明确“稳定可用字段”，为后续演进预留空间。
3. 边界条件：新增协议对象时必须同步更新 `__init__.py` 和 `__all__`。
4. 失败模式：入口没导出会导致上层模块导入失败，或出现隐式依赖内部路径。

### 名词对位讲解

这里有两个很容易被看轻的词：

1. `export`：对外导出，不只是“写出来给别人 import”，而是在声明“这是稳定入口”。
2. `public surface`：公共暴露面，意味着后续章节默认应该依赖这里，而不是直接 import 内部文件。

所以 `domain/__init__.py` 的价值不是“少打一层路径”，而是把 Protocol 的公共边界固定下来。

### 第 3 步：写 Protocol 核心 Schema

创建命令：

```bash
touch src/agent_forge/components/protocol/domain/schemas.py
```

```powershell
New-Item -ItemType File -Force "src\\agent_forge\\components\\protocol\\domain\\schemas.py" | Out-Null
```
文件：[src/agent_forge/components/protocol/domain/schemas.py](../../src/agent_forge/components/protocol/domain/schemas.py)

```python
﻿"""Protocol 组件（框架契约层）。

为什么单独做这一层：
1. 让 Engine、Model Runtime、Tool Runtime 共享同一套数据契约。
2. 给 Observability/Evaluator 提供稳定的结构化输入。
3. 通过版本字段控制协议演进，避免“改一个字段全链路崩”。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

PROTOCOL_VERSION = "v1"


def _now_iso() -> str:
    """统一事件时间格式。

    使用 UTC ISO 字符串，便于日志系统、数据仓库和跨时区排查统一处理。
    """

    return datetime.now(timezone.utc).isoformat()


class ErrorInfo(BaseModel):
    """统一错误结构。

    约束：
    - 所有运行时错误最终都应映射到这里。
    - `retryable` 由 Runtime 层给出，用于指导 Engine 的重试决策。
    """

    error_code: str = Field(..., min_length=1, description="错误码")
    error_message: str = Field(..., min_length=1, description="错误信息")
    retryable: bool = Field(default=False, description="是否可重试")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class AgentMessage(BaseModel):
    """智能体消息对象。

    说明：
    - `role` 用 Literal 固定取值，防止上游传入未知角色破坏上下文拼装。
    - `message_id` 自动生成，确保每条消息都可在 trace 中被唯一定位。
    """

    message_id: str = Field(default_factory=lambda: f"msg_{uuid4().hex}", description="消息 ID")
    role: Literal["system", "developer", "user", "assistant", "tool"] = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, description="消息内容")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    created_at: str = Field(default_factory=_now_iso, description="创建时间")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class ToolCall(BaseModel):
    """工具调用请求。

    说明：
    - `tool_call_id` 是幂等键；重试时可据此避免重复副作用执行。
    - `principal` 预留给权限系统，后续可接入 capability 校验。
    """

    tool_call_id: str = Field(..., min_length=1, description="工具调用唯一 ID")
    tool_name: str = Field(..., min_length=1, description="工具名称")
    args: dict[str, Any] = Field(default_factory=dict, description="工具参数")
    principal: str = Field(..., min_length=1, description="调用主体，用于权限控制")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")

    @field_validator("tool_call_id", "tool_name", "principal")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        # 防止“看起来有值、实际上是空白”的脏数据流入执行链路。
        if not value.strip():
            raise ValueError("字段不能为空白字符")
        return value


class ToolResult(BaseModel):
    """工具调用结果。

    说明：
    - `status` 明确区分成功/失败，避免通过是否有异常字段来“猜状态”。
    - `latency_ms` 是后续可观测性最小指标字段。
    """

    tool_call_id: str = Field(..., min_length=1, description="对应的调用 ID")
    status: Literal["ok", "error"] = Field(..., description="执行状态")
    output: dict[str, Any] = Field(default_factory=dict, description="输出内容")
    error: ErrorInfo | None = Field(default=None, description="错误信息")
    latency_ms: int = Field(default=0, ge=0, description="耗时毫秒")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class ExecutionEvent(BaseModel):
    """执行事件（用于 trace、回放、评测）。

    字段语义：
    - `trace_id`：一次链路的全局 ID。
    - `run_id`：同一 trace 下某次运行实例。
    - `step_id`：运行实例中的步骤定位点。
    """

    trace_id: str = Field(..., min_length=1, description="链路 ID")
    run_id: str = Field(..., min_length=1, description="运行 ID")
    step_id: str = Field(..., min_length=1, description="步骤 ID")
    parent_step_id: str | None = Field(default=None, description="父步骤 ID")
    event_type: Literal["plan", "tool_call", "tool_result", "state_update", "finish", "error"] = Field(
        ..., description="事件类型"
    )
    payload: dict[str, Any] = Field(default_factory=dict, description="事件数据")
    error: ErrorInfo | None = Field(default=None, description="事件错误")
    created_at: str = Field(default_factory=_now_iso, description="创建时间")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class FinalAnswer(BaseModel):
    """结构化最终输出。

    设计目的：
    - 保持领域无关，适用于任意 Agent 任务结果。
    - 让前端展示、评测打分、审计留痕可以直接消费固定字段。
    """

    status: Literal["success", "partial", "failed"] = Field(..., description="任务完成状态")
    summary: str = Field(..., min_length=1, description="结果摘要")
    output: dict[str, Any] = Field(default_factory=dict, description="结构化结果内容")
    artifacts: list[dict[str, Any]] = Field(default_factory=list, description="执行产物清单")
    references: list[str] = Field(default_factory=list, description="可选参考信息")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")


class AgentState(BaseModel):
    """运行状态对象（Engine 的单一事实源）。

    约束：
    - Engine 只读写这个状态对象，不在外部散落临时状态。
    - 未来 snapshot/restore 将基于该对象序列化实现。
    """

    session_id: str = Field(..., min_length=1, description="会话 ID")
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid4().hex}", description="链路 ID")
    run_id: str = Field(default_factory=lambda: f"run_{uuid4().hex}", description="运行 ID")
    messages: list[AgentMessage] = Field(default_factory=list, description="消息列表")
    tool_calls: list[ToolCall] = Field(default_factory=list, description="工具调用记录")
    tool_results: list[ToolResult] = Field(default_factory=list, description="工具结果记录")
    events: list[ExecutionEvent] = Field(default_factory=list, description="执行事件记录")
    final_answer: FinalAnswer | None = Field(default=None, description="最终结构化输出")
    protocol_version: str = Field(default=PROTOCOL_VERSION, description="协议版本")

    @field_validator("session_id")
    @classmethod
    def _session_id_not_blank(cls, value: str) -> str:
        # session_id 是状态分区键，禁止空白可避免跨会话数据污染。
        if not value.strip():
            raise ValueError("session_id 不能为空白字符")
        return value


def build_initial_state(session_id: str) -> AgentState:
    """创建初始状态。

    这是 Engine loop 的标准起点，后续章节统一从这里进入执行流程。
    """

    return AgentState(session_id=session_id)

```

代码讲解：

1. 设计动机：所有核心对象都携带 `protocol_version`，协议演进可追踪。
2. 工程取舍：先保证协议稳定，再考虑字段“优雅”；字段多一点比线上崩溃强。
3. 边界条件：本章只定义协议，不定义业务语义（保持领域无关）。
4. 失败模式：空白字段没拦住会导致幂等键失效、会话分区失效、重试策略失效。

### 主流程拆解：`schemas.py` 到底在保护什么

如果把这一大段代码直接当“数据类集合”来看，很容易低估它。更准确的理解方式是：

1. `AgentMessage / ToolCall / ToolResult` 负责保护运行时输入输出。
2. `ExecutionEvent` 负责保护可观测和回放输入。
3. `FinalAnswer` 负责保护最终交付结构。
4. `AgentState` 负责把前面这些结构收拢成单一事实源。

成功链路例子：

1. 模型生成一条 `ToolCall`。
2. Tool Runtime 返回标准化 `ToolResult`。
3. Engine 把消息、结果、事件都塞回 `AgentState`。
4. 最终输出 `FinalAnswer`，前端和评测都能稳定读取。

失败链路例子：

1. 上游传来空白 `tool_call_id`。
2. 如果没有 `field_validator`，这条记录会进入执行链路。
3. 后续幂等、重试、审计都找不到稳定主键。
4. 最后不是“某个字段不好看”，而是整个运行时行为开始不可预测。

换句话说，`schemas.py` 真正守住的是“系统还能不能继续讲同一种话”。

### 第 4 步：写测试（完整可运行）

创建命令：

```bash
touch tests/unit/test_protocol.py
```

```powershell
New-Item -ItemType File -Force "tests\\unit\\test_protocol.py" | Out-Null
```
文件：[tests/unit/test_protocol.py](../../tests/unit/test_protocol.py)

```python
"""Protocol 组件测试。"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from agent_forge.components.protocol import (
    PROTOCOL_VERSION,
    AgentMessage,
    AgentState,
    ErrorInfo,
    ExecutionEvent,
    FinalAnswer,
    ToolCall,
    ToolResult,
    build_initial_state,
)


def test_initial_state_contains_required_ids_and_version() -> None:
    """初始状态应自动带 trace/run/protocol 字段。"""

    state = build_initial_state("session_001")
    assert state.session_id == "session_001"
    assert state.trace_id.startswith("trace_")
    assert state.run_id.startswith("run_")
    assert state.protocol_version == PROTOCOL_VERSION


def test_protocol_roundtrip_json_serialization() -> None:
    """协议对象应支持 JSON 序列化与反序列化。"""

    message = AgentMessage(role="user", content="公司拖欠工资")
    call = ToolCall(
        tool_call_id="tc_001",
        tool_name="labor_law_search",
        args={"query": "拖欠工资"},
        principal="worker_user",
    )
    result = ToolResult(tool_call_id="tc_001", status="ok", output={"hits": 2}, latency_ms=18)
    event = ExecutionEvent(
        trace_id="trace_001",
        run_id="run_001",
        step_id="step_001",
        event_type="tool_result",
        payload={"tool_call_id": "tc_001"},
    )
    final = FinalAnswer(
        status="success",
        summary="任务已完成并生成结构化结果",
        output={"answer": "工资争议处理建议", "priority": "high"},
        artifacts=[{"type": "plan", "id": "plan_001"}],
        references=["labor_law_search:doc_123"],
    )
    state = AgentState(
        session_id="session_002",
        messages=[message],
        tool_calls=[call],
        tool_results=[result],
        events=[event],
        final_answer=final,
    )

    raw = state.model_dump_json(ensure_ascii=False)
    data = json.loads(raw)
    loaded = AgentState.model_validate(data)
    assert loaded.session_id == "session_002"
    assert loaded.tool_calls[0].tool_name == "labor_law_search"
    assert loaded.final_answer is not None
    assert loaded.final_answer.protocol_version == PROTOCOL_VERSION
    assert loaded.final_answer.status == "success"


def test_blank_fields_must_fail_validation() -> None:
    """空白关键字段必须校验失败。"""

    with pytest.raises(ValidationError):
        ToolCall(tool_call_id=" ", tool_name="t", args={}, principal="p")

    with pytest.raises(ValidationError):
        AgentState(session_id="   ")


def test_error_info_schema() -> None:
    """错误结构应稳定且带协议版本。"""

    err = ErrorInfo(error_code="TOOL_TIMEOUT", error_message="tool timeout", retryable=True)
    assert err.retryable is True
    assert err.protocol_version == PROTOCOL_VERSION


```

代码讲解：

1. 覆盖目标：初始化、序列化、校验、错误模型四类最小稳定面。
2. 断言设计：不只断言“有值”，还断言版本字段和关键状态字段。
3. 失败注入：用空白字符串触发校验，验证协议边界确实生效。
4. 工程价值：后续任何组件改动只要破坏协议，这组测试会第一时间报警。

### 测试为什么重要

这一章的测试不是在证明“Pydantic 会工作”，而是在锁 Protocol 的行为不变量：

1. `build_initial_state()` 生成的状态必须天然可进入主链路。
2. 协议对象必须能 JSON 往返，否则回放、持久化、审计都会失效。
3. 关键 ID 字段不能接受空白值，否则幂等和隔离都会失效。
4. 错误对象必须结构稳定，否则上游只能把错误当字符串处理。

> 这组测试不是“单测装饰品”，而是后续所有组件默认站立的地基验收。

## 运行命令

验证：

```bash
uv run pytest tests/unit/test_protocol.py -q
```


## 增量闭环验证

1. 协议闭环：`AgentState` 与核心对象可序列化/反序列化。
2. 边界闭环：空白关键字段会被校验器拦截。
3. 架构闭环：Protocol 已成为后续组件的稳定契约入口。

## 验证清单

1. `tests/unit/test_protocol.py` 测试通过。
2. `AgentState` 的 `trace_id/run_id/protocol_version` 自动生成并可追踪。
3. 空白关键字段能稳定触发 `ValidationError`，边界校验有效。

## 常见问题

1. 报错：`ModuleNotFoundError: No module named 'agent_forge'`  
修复：确认 [tests/conftest.py](../../tests/conftest.py) 存在，且 `SRC = ROOT / "src"` 未改错。
2. 报错：`ValidationError` 但看不懂字段  
修复：先看 `ToolCall` 和 `AgentState` 的校验器，重点检查是否传入空白字符串。

## 本章 DoD

1. Protocol 核心对象全部可序列化和反序列化。
2. 关键输入边界（空白字段）被协议层拦截。
3. 你能清楚回答每个对象“为什么存在”。

## 下一章预告

1. 第三章进入 Engine 主循环，严格实现：`plan -> act -> observe -> reflect -> update -> finish`。
2. 你会看到 Protocol 如何被 Engine 实际消费，以及为什么 reflect 不应该被省略。
