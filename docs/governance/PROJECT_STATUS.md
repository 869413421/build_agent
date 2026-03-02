# 项目状态（交接单一事实源）

## 当前阶段

- 阶段：仓库结构重构完成（`agent_forge` 命名、`src/` 布局、组件分层落地）
- 日期：2026-03-02

## 已完成组件

- [x] Protocol
- [x] Engine（loop）
- [x] Model Runtime（LLM Adapter）
- [ ] Tool Runtime（API Adapter）
- [ ] Observability
- [ ] Context Engineering
- [ ] Retrieval
- [ ] Memory
- [ ] Evaluator
- [ ] Safety Layer

## 进行中组件（唯一）

- Tool Runtime（API Adapter）（初始化中）

## 已通过审核的小步

1. 规则文件中文化与小步约束落地（`docs/governance/NORTH_STAR.md`、`docs/governance/AI_TASK_GUARDRAILS.md`、`AGENTS.md`）
2. 教程目录骨架创建（`docs/tutorials/01..14`）
3. Protocol 组件完成并升级教程质量（`src/agent_forge/components/protocol/`、`tests/unit/test_protocol.py`）
4. Protocol 代码结构工程化重构（迁移到 `src/agent_forge/components/protocol/`）并新增系列第一章总览教程
5. 系列第二章 Protocol 教程完成（读者向发布文风，未引入 Engine 实现）
6. Engine（loop）组件实现完成（`src/agent_forge/components/engine/application/loop.py`、`tests/unit/test_engine.py`、第三章教程）
7. Engine 升级：加入 reflect 机制、恢复一致性、隔离上下文与性能指标输出
8. Engine 关键修复：stable step key、executed_steps 计数、retry 内 run budget 检查、act_executor 超时执行语义
9. Engine 性能语义增强：共享线程池复用、并发背压、attempt_count 指标、trace 输出摘要化
10. 第三章教程已改为“完整代码版”（`__init__.py`、`loop.py`、`test_engine.py` 全文贴出，可直接复制搭建）。
11. 已将“教程代码必须完整可运行 + 路径可点击跳转”升级为硬约束并写入模板。
12. Engine 已完成 `asyncio + 协程` 重构并通过回归测试（`11 passed`）。
13. 已新增硬约束：教程中禁止使用“完整见仓库”等截断写法，核心示例与测试代码必须文内完整展示。
14. 已新增硬约束：教程每段关键代码后必须提供“代码讲解”（设计动机/取舍/边界/失败模式）。
15. 第三章已同步升级为“完整代码 + 逐段代码讲解”版本，满足发布与学习双目标。
16. 第三章讲解已再次加深：新增执行链路图、失败链路推演、测试取舍说明，避免“只有结论没有推理”。
17. 已新增教程结构硬约束：“先讲面（主流程）再讲点（关键实现）”，并同步到规则文件。
18. 第一、二、三章已按“先面后点”统一重写关键段落，保证系列风格一致。
19. 第三章讲解深度升级为“主流程时间线 + 关键函数解剖 + 状态机视角 + 预算语义深挖 + 评审清单”。
24. Engine（loop）已完成并保持完成态；当前仅对 Model Runtime 做增量优化，不回退 Engine 组件状态。
25. Model Runtime 已按评审意见重构为 `ModelRequest(..., **kwargs)` 动态参数透传，并支持 `runtime.generate(..., **kwargs)` 覆盖。
26. Model Runtime 适配器已拆分为独立目录 `src/agent_forge/components/model_runtime/infrastructure/adapters/`，`OpenAIAdapter` 与 `DeepSeekAdapter` 分文件实现。
27. 框架命名已从 `labor_agent` 切换为 `agent_forge`，分发名/CLI 分别为 `agent-forge` 与 `agent-forge`。
28. 包布局已迁移到 `src/agent_forge`，并按“组件 + 组件内分层”重构目录。
29. 教程模板已升级为“环境前置 + 章节快照 + 主线同步”结构，并开始按小步重构第一章。
30. 第一章文风已升级为“技术博主叙事风格”，强化承上启下与实操链路解释，避免模板化 AI 味。
31. 教程黄金标准已新增“文风黄金规则”：禁止说明书腔，必须包含真实工程场景、经验表达与承上启下段落。

## 技术债与偏差

1. 当前代码目录已存在多组件一次性实现痕迹，不符合“单组件小步”节奏。
2. 下一步需以 Protocol 为起点，逐步清理并重构流程。
3. 组件顺序已固定为 10 项，不再新增组件条目；缺失能力通过 DoD 约束内化到现有组件。
4. 原 `01-北极星与法律边界.md` 已被系列化第一章替换，后续目录命名需逐步统一为“主标题+章标题”格式。
5. 第一章已升级为读者向发布稿：`01-从0到1工业级Agent框架打造-第一章-为什么你总是做不出可上线的Agent.md`。
6. 第二章已升级为手把手实操稿：`02-从0到1工业级Agent框架打造-第二章-Protocol协议层-手把手实战.md`（相对路径、含完整操作步骤与代码）。
7. 已将“设计解释型注释 + 代码文档同步更新”写入规则，并同步到第二章教程。
8. 已将协议层 `FinalAnswer` 重构为通用字段（status/summary/output/artifacts/references），移除法律场景绑定字段。
9. 第二章已修复 Mermaid 11.12.0 兼容问题（对象图改为 flowchart），并将 Python 命令统一为 uv。
10. 第二章已补全环境安装与缺包兜底步骤（含 pytest not found 处理）。
11. 已新增 IDE 解析配置 `pyrightconfig.json`，并在第二章补充 import 飘红处理步骤。
20. 已新增教程黄金标准与章节模板，用于锁定跨会话质量一致性。
21. 已将“生产可用 + 可扩展性 + Engine 反思链路”升级为硬约束。
22. 已按生产级标准加严 10 组件 DoD（并发隔离、版本治理、熔断限流、脱敏、回放一致性、发布门禁）。
23. Engine 当前默认执行器使用线程超时返回，底层调用不可中断时可能后台继续，后续可升级为协程/进程隔离执行器。
24. 新增 `src/agent_forge/support/config` 与 `src/agent_forge/support/logging` 作为辅助模块（不计入 10 组件主干），用于统一配置与日志。
25. 第四章教程已同步更新为 kwargs 透传与 adapters 目录化架构。
26. 第一章已重构为“可独立搭建版”，新增 `examples/from_zero_to_one/chapter_01` 可运行快照与验证测试。

## 下一步唯一任务

- 若本步审核通过，进入 Tool Runtime（API Adapter）组件实现与第五章教程。

## 阻塞项

- 无

## 会话增量（2026-03-02）

1. 第二章教程已按“技术博主叙事风格 + 先面后点 + 可复制运行”重写，文件：`docs/tutorials/02-从0到1工业级Agent框架打造-第二章-Protocol协议层-手把手实战.md`。
2. 新增 `chapter_02` 独立快照工程：`examples/from_zero_to_one/chapter_02/`，补齐 `pyproject.toml`、`tests/conftest.py`、协议代码与测试。
3. 已完成双路径验证：`uv run pytest examples/from_zero_to_one/chapter_02/tests/unit/test_protocol.py -q` 与 `uv run pytest tests/unit/test_protocol.py -q`，均为 `4 passed`。
4. 已修正第二章中的本机绝对路径表述，统一改为“仓库根目录”；并新增 chapter_02 -> 主线的 Bash/PowerShell 快速同步命令。
5. 第三章已补齐 `chapter_03` 独立快照（engine + protocol + tests + pyproject + conftest），并在第三章教程新增“快照 -> 主线”的快速同步命令（Bash/PowerShell）。
6. 第三章运行命令已改为跨环境可直接执行的 `uv run pytest ... -q`，避免使用仅 Bash 可用的 `UV_CACHE_DIR=...` 前缀写法。
7. 已回归验证：`uv run pytest tests/unit/test_protocol.py tests/unit/test_engine.py -q` 通过（11 passed）。
8. 根据用户反馈，第三章已新增“术语白话卡片”（plan/act/observe/reflect/update/finish 的生活化解释与完整例子），并移除“环境准备与缺包兜底步骤”，降低学习陡峭度。
9. 教程黄金标准已升级：新增“学习曲线控制标准（术语先白话、先最小可跑再深挖、复杂章节阅读路径）”，并将“环境准备与缺包兜底”调整为按需出现而非每章强制。
10. 第四章已按新标准重构：新增术语白话卡片、固定“先最小可跑再回归”学习顺序、同步补齐 `chapter_04` 独立快照（model_runtime + support + tests + pyproject + conftest）。
11. 第四章教程已修正与主线一致的目录与导入路径（`support/config/settings.py`、`support/logging/logger.py`、`model_runtime/infrastructure/adapters/*`），并新增 Bash/PowerShell 主线同步命令。
12. 验证结果：`tests/unit/test_model_runtime.py` 在主线与 chapter_04 快照均通过（7 passed）；`tests/unit/test_protocol.py + tests/unit/test_engine.py + tests/unit/test_model_runtime.py` 主线回归通过（18 passed）。
13. 第四章已补齐“通用 config/logging 集成”到代码与教程：`model_runtime` 与 adapters 统一使用 `support/config/settings.py`、`support/logging/logger.py`，并在教程中新增集成说明与边界说明。
14. 第四章新增 DeepSeek 真实调用打通入口：`src/agent_forge/apps/model_runtime_deepseek_demo.py`（支持 `uv run python -m ...`），并同步到 chapter_04 快照与教程。
15. 根据用户审阅意见，`DeepSeek` 真实调用不再作为自动化测试用例；改为教程中的“手动线上打通步骤”（`uv run python -m agent_forge.apps.model_runtime_deepseek_demo ...`）并保留 `test_model_runtime.py` 作为自动化回归。
16. 第四章已重排步骤顺序：先前置 support(config/logging) 集成并给出完整代码讲解，再进入 model_runtime 主干实现，避免读者认知断层。



17. 教程硬标准已升级为 创建目录+创建文件命令 强约束，并已回补第 01~04 章（Bash + PowerShell 双版本，路径与快照代码一致）。


18. 第一章教程已重构为课程开篇版：补齐适用人群/知识前置/课程展望，并将创建命令改为与代码步骤一一对应的分步执行（非批量一次性创建）。

19. 第二章已按文件前置创建命令代码块规范补齐：每个“文件：”段前均新增 bash + powershell 创建命令。
20. 第三、第四章已按文件前置创建命令代码块规范补齐：每个“文件：”段前均新增 bash + powershell 创建命令。

21. 章节承接规范已落地：第02~04章开篇新增“复制上一章 examples 快照”步骤，并写入教程黄金标准与模板。