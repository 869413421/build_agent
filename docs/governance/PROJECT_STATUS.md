# 项目状态（交接单一事实源）

## 当前阶段

- 阶段：Retrieval 组件落地完成（代码 + 测试 + 教程）
- 日期：2026-03-07

## 已完成组件

- [x] Protocol
- [x] Engine（loop）
- [x] Model Runtime（LLM Adapter）
- [x] Tool Runtime（API Adapter）
- [x] Observability
- [x] Context Engineering
- [x] Retrieval
- [ ] Memory
- [ ] Evaluator
- [ ] Safety Layer

## 进行中组件（唯一）

- Memory

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

- 若本步审核通过，进入第九章 Memory 组件实现与教程同步。

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
14. 第四章新增 DeepSeek 真实调用打通入口：`examples/model_runtime/deepseek_demo.py`（支持 `uv run python -m ...`），并同步到 chapter_04 快照与教程。
15. 根据用户审阅意见，`DeepSeek` 真实调用不再作为自动化测试用例；改为教程中的“手动线上打通步骤”（`uv run python examples/model_runtime/deepseek_demo.py ...`）并保留 `test_model_runtime.py` 作为自动化回归。
16. 第四章已重排步骤顺序：先前置 support(config/logging) 集成并给出完整代码讲解，再进入 model_runtime 主干实现，避免读者认知断层。



17. 教程硬标准已升级为 创建目录+创建文件命令 强约束，并已回补第 01~04 章（Bash + PowerShell 双版本，路径与快照代码一致）。


18. 第一章教程已重构为课程开篇版：补齐适用人群/知识前置/课程展望，并将创建命令改为与代码步骤一一对应的分步执行（非批量一次性创建）。

19. 第二章已按文件前置创建命令代码块规范补齐：每个“文件：”段前均新增 bash + powershell 创建命令。
20. 第三、第四章已按文件前置创建命令代码块规范补齐：每个“文件：”段前均新增 bash + powershell 创建命令。

21. 章节承接规范已落地：第02~04章开篇新增“复制上一章 examples 快照”步骤，并写入教程黄金标准与模板。
22. CLI 子命令模式已固定：主线与 chapter_01 快照均新增 @app.callback()，避免单命令模式导致 agent-forge version 解析失败；第一章教程已同步说明该机制。

23. 第一章教程已补充 CLI 子命令修复后的验证闭环：新增主线命令预期输出，并新增 uv sync --dev 刷新入口步骤。

24. 教程体系已切换为主线单轨：重写 docs/tutorials/_TUTORIAL_GOLD_STANDARD.md 与 docs/tutorials/_CHAPTER_TEMPLATE.md，新增 docs/tutorials/_CHAPTER_INDEX.md（Tag 回放索引）。
25. 01~04 章教程已完成去快照迁移：移除 examples/from_zero_to_one/chapter_* 路径引用与‘复制快照/同步快照’流程，统一锚定 src/tests 主线。
26. 已执行快照目录清理：chapter_01/02 及 chapter_03/04 中可删除内容已移除；剩余 6 个 pytest-cache-files-* 目录因 ACL 拒绝删除（见阻塞项）。

## 阻塞项（更新）
- examples/from_zero_to_one/chapter_03|04 下 6 个 pytest-cache-files-* 目录存在系统 ACL 拒绝，当前会话无权删除；不影响主线代码与教程执行，但会在 git status 中显示权限 warning。

27. 已按用户反馈清理第一章教程中的‘回放迁移噪音措辞’：修复主流程图与第5步文案、补齐空代码块说明、恢复被污染的示例代码字符串（agent_forge_chapter_01）。

28. 第二章教程已修复创建文件命令：纠正错误路径（移除 examples 误路径），并将损坏的单反引号命令恢复为标准 fenced code block（bash/powershell）。
33. 第四章教程已清理“主线同步”空命令块：改为“主线一致性检查”，并补齐 Bash/PowerShell 可执行检查命令（`ls` / `Get-ChildItem`），避免读者执行中断。
34. 第三章教程已复核：无空命令块、命令渲染正常，本次未做多余改动，保持现有教学内容稳定。


35. 第一章教程已按新《_CHAPTER_TEMPLATE.md》与《_TUTORIAL_GOLD_STANDARD.md》完成增量优化（非重构）：补齐“架构位置说明”“本章主线改动范围”“增量闭环验证”，并将“跑起来看看”统一为“运行命令”，同时补充 PowerShell 等价命令。
36. 第一章运行命令区预期输出已修正为 `agent-forge-chapter-01`，与当前 CLI 实际行为一致。
37. 第二章教程已按新模板/新标准完成增量优化（非重构）：补齐“架构位置说明”“本章主线改动范围”“增量闭环验证”，运行命令补全 PowerShell 等价命令，并修正“主线 主线”等小文案瑕疵。
38. 第三章教程已按新模板/新标准完成增量优化（非重构）：补齐“架构位置说明”“本章主线改动范围”“增量闭环验证”，运行命令补全 PowerShell 等价命令，新增“本章 DoD/下一章预告”并补齐第1步目录创建的 Bash 子目录命令。
39. 第三章教程“创建导出文件”已修复代码漂移：`engine/__init__.py` 示例导入改为 `agent_forge.components.engine.application.loop`，并同步修正文案中的导入边界描述。
40. 已新增文章质检技能 `skills/tutorial-quality-checker`：包含 `SKILL.md` 与自动检查脚本 `scripts/check_tutorial_markers.py`，可检查章节结构、命令块空块、文件创建命令缺失与文件路径标记问题。
41. 质检脚本已增强为关键词匹配，减少标题微差异误报；已在第三章上验证通过。
42. 第四章教程已按新模板补齐缺失段落：新增“架构位置说明”“本章主线改动范围”“增量闭环验证”“本章 DoD”“下一章预告”，并补全运行命令 PowerShell 等价块；经 tutorial-quality-checker 校验通过。
43. tutorial-quality-checker 已升级：新增“代码漂移”自动检查（文件标记后的代码块与真实文件逐项对比），并将其纳入默认检查流程。
44. 已完成第四章代码漂移修复：按主线真实文件对齐 `settings.py`、`logger.py`、`schemas.py`、`model_runtime_deepseek_demo.py` 教程代码块；并升级质检脚本支持 BOM 兼容，避免 UTF-8-BOM 文件误报漂移。
45. 第四章已补齐“环境准备与缺包兜底”段落（uv add + uv sync 可复制命令），并将 DeepSeek 手动打通从临时环境变量改为 `.env` 配置方式；常见问题同步改为 `.env` 排查路径。
46. 第四章已按“model_runtime 全量代码可复制”标准补齐：新增 `model_runtime` 各层 `__init__.py`、`infrastructure/adapters/stub.py` 的完整代码与创建命令，并补全 `base.py/openai_adapter.py/deepseek_adapter.py/runtime.py/test_model_runtime.py` 全文展示；同时修正真实文件清单中 `contracts.py` 错误路径为 `schemas.py`，经 `tutorial-quality-checker` 复检通过。
47. 根据审阅反馈，第四章已把缺失的 `__init__.py` 前置到对应实现步骤（domain / infrastructure / adapters / application），并清理第 5.5 步重复段落；同时将“包目录必须同步创建并展示 `__init__.py`”写入 `docs/tutorials/_TUTORIAL_GOLD_STANDARD.md` 与 `docs/tutorials/_CHAPTER_TEMPLATE.md` 作为硬约束，复检通过。
48. 已修复 `.env` BOM 兼容问题：`src/agent_forge/support/config/settings.py` 改为 `load_dotenv(..., encoding=\"utf-8-sig\")` 且 `env_file_encoding=\"utf-8-sig\"`；第四章 PowerShell `.env` 创建命令改为无 BOM 写入，并新增 BOM 排查/重写步骤，避免 `\ufeffAF_DEEPSEEK_API_KEY` 读不到。
49. 已将 `response_format` 调整为通用可透传策略：优先透传调用方传入的 `response_format`（如 `json_object`），未传入且存在 `response_schema` 时默认走 `json_schema`；若服务端返回 `response_format unavailable`，适配器自动降级为 `json_object` 再试一次。同步补充单测并更新第四章对应代码块与说明，复检通过。
50. `model_runtime_deepseek_demo` 已从 `src/agent_forge/apps/` 迁移至 `examples/model_runtime/deepseek_demo.py`，第四章所有创建命令/文件路径/运行命令已同步到 `examples`，避免将教学脚本误归类为应用入口。

51. README 已新增“课程索引（按章节）”，包含 01~04 章直达链接与 05~14 章状态占位，便于读者按章节导航与后续持续发布。
52. Model Runtime 已完成流式能力：新增 `stream_generate` 与 `ModelStreamEvent(start/delta/usage/error/end)`，并保留 `generate` 兼容路径；同时落地最小 hooks（before_request/on_stream_event/after_response）与失败边界收尾语义。
53. 已新增流式单测 `tests/unit/test_model_runtime_stream.py`，并完成回归验证：`uv run pytest -q` 通过（23 passed）。
54. 第四章教程已完成“先代码后教程”的重组入口：新增流式主线与增量改动导航，且原有章节内容未删减。
55. `examples/model_runtime/deepseek_demo.py` 已重写为真实双链路示例：新增 `--mode non-stream|stream|both`，同一脚本可分别验证结构化非流式与增量流式输出。
56. 已新增 `tests/unit/test_deepseek_demo.py`，通过注入 `StubDeepSeekAdapter` 验证 `run_deepseek_once` 与 `run_deepseek_stream` 两条路径均可执行，避免示例脚本后续回归失效。
57. 第四章教程中的 `deepseek_demo.py` 完整代码块与运行命令已同步为双链路版本（含 Bash/PowerShell 双命令），在不删除既有章节的前提下完成增量更新。
58. 已补齐非流式可观测性对称性：`ModelRuntime.generate(request, hooks=None, **kwargs)` 现支持与流式一致的 `before_request/after_response` hooks 接入。
59. 已新增单测覆盖非流式 hooks：`tests/unit/test_model_runtime.py::test_generate_should_call_hooks_for_non_stream`，验证 non-stream 也可注入观测逻辑。
60. 第四章教程已按“面向读者从0到1”整章重写：移除补丁式重组前言，改为目标->架构->前置->实施步骤->运行命令->验证清单->常见问题->DoD->下一章预告的单线教学结构。
61. 第四章关键代码块已从主线文件自动同步并通过代码一致性检查（文件标记后的代码块与仓库真实文件逐项比对通过），满足“完整代码、无代码漂移”要求。
62. 已修复第四章教程乱码问题：回滚到 Git 中 UTF-8 原文后再重排章节入口，避免 PowerShell 编码页导致的“?”污染。
63. 第四章已按读者视角从章节标题直接进入正文（移除“重组说明”前言），并保持全部代码块与主线文件一致（无代码漂移）。

64. Tool Runtime 代码主干已落地：新增 `domain/application/infrastructure` 分层实现，包含工具注册、参数校验、能力校验、幂等缓存、超时执行、统一错误映射与执行记录。
65. 已实现两个示例工具：`python_math`（AST 白名单安全求值）与 `tavily_search`（官方 SDK 接入，支持 mock client 注入）。
66. 已新增 Tool Runtime 单测与 Engine 零侵入集成测试：`tests/unit/test_tool_runtime.py`、`tests/unit/test_tool_runtime_engine_integration.py`。
67. 已新增可运行示例脚本：`examples/tool_runtime/tool_runtime_demo.py`，可分别验证数学工具与 Tavily 搜索工具执行链路。
68. 回归结果：`uv run --no-sync pytest tests/unit/test_tool_runtime.py tests/unit/test_tool_runtime_engine_integration.py -q` 通过（10 passed）；`uv run --no-sync pytest -q` 通过（36 passed）。
69. 受当前网络限制，`uv run` 常规模式会触发在线拉取依赖失败（os error 10013），本次使用 `--no-sync` 进行离线回归验证。
70. Tool Runtime 已补齐高级特性：新增 `execute_async`、`ToolRuntimeHooks`（before/on_event/after/on_error）与链式调用 `run_chain/arun_chain`。
71. 已新增高级特性回归测试（hooks/async/chain），并修复前置校验失败未触发 `on_error` 的缺陷。
72. 最新回归：`uv run --no-sync pytest -q` 通过（39 passed）。
73. Tool Runtime 结构已工程化重构：`ToolRuntime` 仅保留门面职责，异步执行与链式编排拆分为 `ToolExecutor`、`ToolChainRunner`，hooks 分发拆分为 `HookDispatcher`。
74. 重构后行为保持兼容，工具相关测试与全量回归均通过（39 passed）。
75. Tool Runtime 执行主流程与链式编排主流程已补齐分步注释（1/2/3），覆盖执行门禁、重试、错误收口与链路短路边界。
76. 已新增异步批量执行接口 `execute_many_async(tool_calls, max_concurrency)`，支持并发上限与顺序稳定返回。
77. 新增批量异步执行测试与并发参数校验测试，回归通过（41 passed）。
78. 已增强 `examples/tool_runtime/tool_runtime_demo.py` 的可测试性：拆分为 `create_demo_runtime/run_math_once/run_tavily_once/run_math_batch_async`，CLI 仅做参数解析与输出。
79. 已新增 `tests/unit/test_tool_runtime_demo.py`，覆盖 5 个 demo 场景（数学成功/数学非法表达式/Tavily mock/批量执行/顺序稳定）。
80. 全量回归更新：`uv run --no-sync pytest -q` 通过（46 passed）。
81. 已在 `tool_runtime_demo.py` 增加工具链示例入口 `run_tool_chain_once` 与 CLI 参数 `--run-chain`。
82. `test_tool_runtime_demo.py` 已新增工具链成功与失败短路测试，demo 测试扩展为 7 个用例。
83. 全量回归更新：`uv run --no-sync pytest -q` 通过（48 passed）。
84. 已新增硬约束：业务代码每个方法必须有 docstring，且需包含参数级说明（Args）与返回值说明（Returns），异常分支补 Raises。
85. 已对 Tool Runtime 相关主代码补齐方法级参数注释（门面/执行器/链路编排/hooks/工具实现/demo 函数）。
86. 为兼容 `tests.unit.conftest` 绝对导入，新增 `tests/__init__.py` 与 `tests/unit/__init__.py` 包标记。
87. 最新回归：`uv run --no-sync pytest -q` 通过（48 passed）。
88. 第五章 Mermaid 架构图已改为 Mermaid 11.12.0 兼容写法（移除复杂 subgraph 语法，改为扁平节点关系）。
89. 已新增教程规则：大文件可节选，但必须紧邻提示“本段为节选 + 可点击源码路径 + 进入文件复制完整代码后再运行”。
90. 第五章教程已升级为“通俗讲解增强版”：新增白话场景例子、执行时序图、失败推演与工程取舍扩展，降低阅读门槛。
91. 已按用户要求对大文件节选位置补齐“请打开源码复制完整代码”提醒，并明确 `__init__.py` 导出文件可简讲。
92. 教程黄金标准与章节模板已新增“讲解表达规则”：通俗化、举例化、图示化；历史章节升级仅允许追加，禁止删减原文与原代码。
93. 已完成第01~04章讲解升级（增量追加补充段）：每章新增白话解释、成功/失败例子与流程图/时序图，不改删原内容。
94. 已根据用户反馈补强第五章：第4步新增 ChainRunner 代码示例；第5/6步新增通俗讲解与真实例子；补充 Demo 脚本创建命令与核心代码节选提示。
95. 已将“禁止补丁式写作、必须自然融合主线叙事”写入教程黄金标准、章节模板与 AI 执行硬约束。
96. 已完成第01~04章自然融合式优化：第02/03章移除“附录式”补丁标题并改为主线化“深入理解”章节标题；第04章新增同风格“深入理解”收束章节（含成功/失败链路与流程图），全程未删减原有内容与代码。
97. 已按用户反馈完成第01~04章结构重排：将“深入理解”从文末整体前移到正文前半段（进入主线改动范围/实施步骤前），改为先建立认知再看实现，消除“读到最后才补概念”的断层。
98. 第五章已补齐 `chain_runner.py` 深度代码讲解：新增主流程拆解、成功/失败链路示例、链式数据流流程图与编排时序图，并补充工程取舍与高频失败边界说明，内容已自然融合至第4步正文。
99. 已将“主要代码讲解深度统一到 `chain_runner.py` 级别”升级为黄金法则：同步写入 `docs/tutorials/_TUTORIAL_GOLD_STANDARD.md`、`docs/tutorials/_CHAPTER_TEMPLATE.md` 与 `docs/governance/AI_TASK_GUARDRAILS.md`。
100. 已新增技能 `skills/publish-grade-article-auditor`：支持出版级文章深度审核与主动优化，内置“代码零删减”守卫脚本 `code_block_guard.py`（inventory/verify），用于优化前后自动校验代码块不丢失。
101. 已修复技能加载失败问题：将 `.agents/skills/publish-grade-article-auditor/SKILL.md` 转换为 UTF-8 无 BOM，确保 YAML frontmatter 从首字节 `---` 开始可被解析；并同步校正 `.agents/skills/tutorial-quality-checker/SKILL.md` 为 UTF-8 无 BOM，避免同类隐患。
102. 已按 `publish-grade-article-auditor` 完成第一章出版级增量优化：围绕 `pyproject.toml`、`cli.py`、`api/app.py`、`conftest.py`、`test_bootstrap.py` 补齐“主流程拆解 + 成功/失败链路 + 图示 + 工程取舍/边界”，并新增“环境准备与缺包兜底步骤（可复制命令）”。
103. 第一章已完成“代码零删减”双阶段校验：优化前 inventory 记录 28 个代码块，优化后 verify 通过（before=28, now=36），确认未删除任何原有代码块。
104. 已修复第一章 Mermaid 渲染兼容问题：将高风险图语法改为 11.12.0 稳定写法（纯文本节点、去除易歧义符号与括号别名），消除 `Syntax error in text`。
105. 已将 Mermaid 11.12.0 兼容规则固化到标准与护栏：`docs/tutorials/_TUTORIAL_GOLD_STANDARD.md`、`docs/tutorials/_CHAPTER_TEMPLATE.md`、`docs/governance/AI_TASK_GUARDRAILS.md`，后续教程优化默认执行该约束。
106. 已使用 `publish-grade-article-auditor` 完成第 02~05 章出版级增量优化：保守精简重复叙述、补齐工程可执行兜底命令、统一术语与承接文案，不删减原有代码块。
107. 第 02~05 章已完成代码零删减校验并全部通过：`02(before=21, now=24)`、`03(before=22, now=22)`、`04(before=74, now=77)`、`05(before=45, now=49)`。
108. 第 05 章已修正章节承接与运行说明一致性：补齐 PowerShell/`python` 兜底命令，统一 DoD 标题风格，并将下一章预告调整为 Observability 主线。
109. 已按用户要求再次使用 `publish-grade-article-auditor` 优化第 04 章：重点补强 `support/config+logging`、`adapters/base.py`、`runtime.py`、`test_model_runtime.py`、`deepseek_demo.py` 的主流程拆解、成功/失败链路、图示与工程取舍，且保持正文自然融合。
110. 第 04 章本轮复优化已通过代码零删减校验：`before=75, now=80`，确认未删除任何原有代码块。
111. Re-optimized Chapter 05 with `publish-grade-article-auditor`: added execution-closure sections for environment fallback, run commands, verification checklist, and FAQ while preserving narrative continuity.
112. Chapter 05 passed code-zero-deletion verification: `code_block_guard verify` returned `before=49, now=56, PASS`, confirming no original code block was removed.
113. 已完成 Observability 组件主干实现：新增 `domain/application/infrastructure` 分层（采样、脱敏、trace/metrics/replay 存储、导出与聚合指标）。
114. Engine 已新增可选 `event_listener` 接入点（监听失败仅告警不影响主流程），满足观测横切接入与向后兼容。
115. 已新增 `ToolRuntimeObservabilityHook` 并打通 ToolRuntime 事件与工具结果录制链路。
116. 已新增 Observability 单测 `tests/unit/test_observability.py`，并补充 Engine 监听容错测试。
117. 回归结果：`uv run --no-sync pytest -q` 通过（53 passed）。
118. 已新增第六章教程：`docs/tutorials/06-从0到1工业级Agent框架打造-第六章-Observability-可观测与回放闭环.md`。
119. README 课程索引已同步：第 05/06 章状态改为已完成并补齐链接。
120. 已完成 Observability 质检修复：工具观测上下文改为任务级隔离（`ContextVar`），消除并发 run 串写 `trace_id/run_id` 风险。
121. 已修复 replay 完整性：工具失败结果也进入 `after_execute` 收口并写入回放记录，不再只记录成功调用。
122. Tool Runtime 执行器错误路径已统一持久化记录（含 timeout/执行异常/前置校验失败），观测数据与执行记录语义对齐。
123. 已补充并发隔离与失败回放回归测试（`test_observability_should_not_mix_context_across_concurrent_tasks`、`test_observability_should_record_failed_tool_result_in_replay`、`test_tool_runtime_should_return_timeout_error` 记录断言）。
124. 最新全量回归：`uv run --no-sync pytest -q` 通过（55 passed）。
125. 已按用户反馈重构第六章教程结构，补齐模板必需段落（目标、前置条件、环境兜底、运行命令、验证清单、常见问题、DoD、下一章预告）。
126. 第六章已从“占位式源码引用”升级为“可复制可运行的完整代码讲解版”，核心文件与测试均提供全文代码块。
127. 已完成第六章教程质检脚本复检：`tutorial-quality-checker` 结构检查通过。
128. 已完成第六章代码块守卫校验：`code_block_guard verify` 通过（before=33, now=33），确认未发生代码块删减。
129. 根据用户反馈，第六章已追加“术语白话卡片”，先讲清 trace/metric/replay/sampling/redaction 的工程语义，再进入代码实现。
130. 第六章已追加“两条真实链路案例（成功+失败）”，并给出输入输出级别的可验证结果，避免抽象讲解。
131. 第六章已追加 runtime 主流程 1/2/3/4 分步走读与 hook 高风险踩坑点说明，强化“主流程机制 + 失败推演 + 取舍边界”。
132. 第六章本轮复检结果：`tutorial-quality-checker` 再次通过（PASS）。
133. 已修复第六章文件创建命令顺序：改为“先创建目录，再创建文件”，并逐条对应讲解步骤。
134. 已补齐第六章 Python 包初始化文件创建命令：`observability/__init__.py`、`domain/__init__.py`、`application/__init__.py`、`infrastructure/__init__.py`。
135. 已按用户反馈重排第六章创建步骤：不再把所有创建命令堆在第 2 步，改为第 3~9 步“讲到哪创建到哪”。
136. 第六章创建命令已统一为“先创建目录，再创建 `__init__.py`（包目录），再创建当前文件”的顺序。
137. 第六章重排后已再次通过 `tutorial-quality-checker` 结构检查（PASS）。
138. 已按用户要求将第六章所有命令块统一改为 ` ```codex ` 包裹格式，不再使用 `bash/powershell` 代码块标签。
139. 已重建第六章文档内容并修复编码污染问题，确保中文标题与正文可正常显示。
140. 已修复第六章内容丢失问题：7 段占位代码块已恢复为对应源码与测试的完整代码内容。
141. 第六章当前命令块统一为 ` ```codex ` 格式，同时保留“先目录、再 `__init__.py`、再目标文件”的创建顺序。
142. 第六章修复后已通过 `tutorial-quality-checker` 结构复检（PASS）。
143. 已修复第六章 Markdown 代码栅栏错位：为缺失的 python 代码块补全结束栅栏，消除‘正文被代码块吞并’问题。
144. 第六章修复后已通过双重复检：代码栅栏配对检查 FENCES_BALANCED，	utorial-quality-checker 结构检查 PASS。
145. 已按用户要求将第六章讲解深度对标第五章：为 schemas/interfaces/policies/memory/runtime/hooks/tests 全部补齐主流程拆解、成功/失败案例与工程取舍说明。
146. 第六章本轮升级已通过三项校验：code_block_guard 零删减 PASS（before=19, now=20）、tutorial-quality-checker PASS、代码栅栏配对 FENCES_BALANCED。
147. 已修复第六章中文编码污染：删除 7 段异常 ? 讲解块并替换为正常中文深度讲解，当前 ? 匹配计数为 0。
148. 修复后校验通过：tutorial-quality-checker PASS，code_block_guard verify PASS（before=19, now=20）。
149. 已按用户反馈修正第六章表述歧义：明确 Engine 提供的是 event_listener 注入点，engine_event_listener 为 ObservabilityRuntime 提供的回调实现。
150. 已新增 examples/observability/observability_demo.py 并在第六章加入完整示例代码与运行命令；本地以 PYTHONPATH=src python ... 验证可运行。
151. 已补齐第六章 4 个 __init__.py 的完整源码块与创建命令，消除读者按教程创建后 import 报错问题。
152. 已将第五章 	est_tool_runtime.py 以主线步骤自然补齐：新增创建命令、完整代码与代码讲解，消除读者执行时缺文件问题。
153. 第五章已新增 tests/unit/conftest.py 主线步骤（创建命令+完整代码+讲解），并将 test_tool_runtime.py 顺延为下一步，避免读者按教程执行时导入失败。
154. 第五章已补充 tests/__init__.py 与 tests/unit/__init__.py 主线步骤（创建命令+完整代码），确保 tests 包绝对导入路径稳定。
155. 已修复用户反馈的 failed-tool replay 空记录问题：增强 ToolRuntimeObservabilityHook，在 error 事件阶段做兼容兜底录制，并补充回归测试。
156. 第六章已同步说明 loop.py 变更（EngineLoop event_listener 注入点）与该失败用例排错路径。
158. 已完成 ModelRuntime Hook 级接入：新增 ContextEngineeringHook，在 before_request 阶段注入上下文编排与预算裁剪，并写入 context_budget_report 供观测/调试。
157. 已完成第七章 Context Engineering 代码主线落地：新增 domain/application/infrastructure 分层，包含 ContextBudget/ContextBundle/BudgetReport/CitationItem、保守裁剪策略与轻量 token 估算器。
159. 已新增第七章单测 tests/unit/test_context_engineering.py（6 个用例）并验证通过；全量回归 uv run --no-sync pytest -q 通过（61 passed）。
160. 已完成 Context Engineering 代码质检修复：ContextEngineeringHook 不再覆盖调用方已设置的 ModelRequest.tools，改为优先继承 request.tools，再回退 hook 默认工具。
161. 已修复 citations 未进入模型上下文的问题：保留的 citations 会被物化为 developer 消息，并与预算估算采用同一渲染格式，避免“报告通过但实际超预算”。
162. 已修复极限预算边界：mandatory message 改为截断而非直接丢弃，truncate_text 在超小预算下不再因追加截断标记导致反超预算。
163. 已补充 Context Engineering 回归测试至 9 条，并完成全量回归：uv run --no-sync pytest -q 通过（64 passed）。
164. 已按用户要求完成 Context Engineering 相关代码注释/docstring 中文化（application/domain/infrastructure 与对应单测），并复测通过（64 passed）。
165. 已完成二轮质检修复：ModelRuntime 适配器过滤内部 extra 字段（context_budget_report/citations/tools），避免 Context Engineering 内部字段透传到厂商 API。
166. 已修复 Context Engineering 策略层类型导入问题：`policies.py` 补回 `typing.Any`，消除静态检查错误。
167. 已新增回归测试 `test_adapter_should_not_forward_internal_context_extras` 并通过；全量回归 `uv run --no-sync pytest -q` 通过（65 passed）。
168. 已完成第七章教程：`docs/tutorials/07-从0到1工业级Agent框架打造-第七章-ContextEngineering-上下文编排与预算治理.md`，结构对齐章节模板，讲解深度对齐第五章。
169. 第七章教程已补齐 `__init__.py` 创建步骤、完整源码、Hook 接线说明、预算治理主流程图、成功/失败链路和测试讲解。
170. `README.md` 课程索引已将第 07 章状态更新为已完成并补齐链接。
171. 已新增第七章可运行示例：`examples/context_engineering/context_engineering_demo.py`，用于展示 Hook 改写后的最终请求、tools 保留情况与预算报告。
172. 已新增示例回归测试：`tests/unit/test_context_engineering_demo.py`，并将 examples 目录保持为“非包”用法，测试改为按文件路径加载脚本。
173. 第七章教程已追加 examples 主线步骤、完整示例代码、示例测试代码与退化路径讲解。
174. 最新全量回归：`uv run --no-sync pytest -q` 通过（67 passed）。
175. 已按用户要求对第七章教程再次精修：重点加厚 `policies.py`、`runtime.py`、`hooks.py` 三段主流程讲解，补齐主流程时间线、Mermaid 图、成功链路、失败链路、工程取舍与边界说明。
176. 第七章本轮精修已修复新增讲解段落的编码污染，中文问号污染计数清零（`???=0`，`??=0`）。
177. 第七章本轮精修已通过代码零删减校验：`code_block_guard verify` PASS（before=40, now=43），确认未删除任何原有代码块，仅追加讲解与图示。
178. 已继续加厚第七章测试讲解：为 `tests/unit/test_context_engineering.py` 追加逐条断言解释，明确每条测试分别在锁什么行为不变量、为什么这些断言足够证明实现正确。
179. 已继续加厚第七章 example 测试讲解：为 `tests/unit/test_context_engineering_demo.py` 追加“示例测试锁什么”分析，明确单元测试与示例测试的职责边界。
180. 第七章本轮二次精修已再次通过代码零删减校验：`code_block_guard verify` PASS（before=40, now=44），且中文问号污染复检继续为 0。
181. 已完成第八章 Retrieval 代码主线落地：新增 `domain/application/infrastructure` 分层，提供通用 `Retriever / Reranker / EmbeddingProvider` 协议、`RetrievalQuery / RetrievalResult / RetrievedDocument / RetrievedCitation` 标准类型，以及 `RetrievalRuntime`。
182. 已落地可离线基线后端：新增 `InMemoryRetriever` 与 `NoopReranker`，用于在不绑定具体向量库与重排技术的前提下跑通检索闭环。
183. 已落地真实向量库适配示例：新增 `ChromaRetriever`，通过注入式 `EmbeddingProvider` 对接真实向量检索后端，同时保持主线公共接口不绑定 Chroma。
184. 已新增 Retrieval 单测：`tests/unit/test_retrieval.py`、`tests/unit/test_retrieval_chroma.py`，覆盖本地检索、运行时编排、Context Engineering 引用桥接、Chroma 适配器写入/查询与缺依赖报错。
185. 已更新 `pyproject.toml` 可选依赖组：新增 `retrieval-chroma`，主依赖仍不强制绑定向量库。
186. 已更新 `docs/architecture/interfaces.md`，补充 Retrieval 核心类型与检索版本可追踪约束。
187. 最新全量回归：`uv run --no-sync pytest -q` 通过（77 passed）。
188. 已新增 Retrieval 可运行示例：`examples/retrieval/retrieval_demo.py`，同时展示可离线路径 `InMemoryRetriever` 与真实向量库路径 `ChromaRetriever` 的双轨演示。
189. 已新增示例回归测试：`tests/unit/test_retrieval_demo.py`，覆盖基线路径输出与 Chroma 可选依赖缺失时的可解释降级。
190. 最新全量回归：`uv run --no-sync pytest -q` 通过（79 passed）。
191. 已完成 Retrieval 质检修复：`ChromaRetriever` 现在会把 `RetrievalFilters` 下推为 Chroma `where` 条件，不再先近似召回再客户端裁剪，修复跨后端过滤语义不一致问题。
192. 已完成 Retrieval 质检修复：`ChromaRetriever` 对 metadata 做标量类型收口，遇到 list/dict 等不兼容值时会给出明确错误，避免真实写入阶段隐式炸裂。
193. 已增强 Retrieval 示例韧性：`examples/retrieval/retrieval_demo.py` 现在不仅处理 Chroma 缺依赖，还会对写入/查询阶段异常做可解释降级。
194. 已新增对应回归测试，覆盖 `where` 条件下推、metadata 类型校验与 Chroma 运行期失败降级。
195. 最新全量回归：`uv run --no-sync pytest -q` 通过（82 passed）。
196. 已完成第八章教程正文：`docs/tutorials/08-从0到1工业级Agent框架打造-第八章-Retrieval-检索召回与引用标准化.md`，结构对齐章节模板，讲解深度对齐第五章标准。
197. 第八章教程已把 Retrieval 主线、双轨后端、真实向量库适配示例、examples 与三组测试全部纳入主线，不再停留在抽象概念说明。
198. 第八章教程已明确 `examples/` 为非包目录，未引导创建任何 `examples/__init__.py`，并保留 `ChromaRetriever` 可解释降级链路说明。
199. `README.md` 已将第 08 章状态更新为已完成，并补齐教程链接。
200. 已完成第八章教程收尾修复：补齐 `验证清单`、`常见问题`、`本章 DoD`、`下一章预告` 四个缺失章节，并修复此前一次终端编码导致的尾部中文污染。
201. 已修正第八章教程中的文件路径展示方式：相关源码、示例与测试路径改为可点击 Markdown 链接，且链接目标改为相对 `docs/tutorials/` 的真实路径。
202. 已复跑教程结构检查脚本：第八章当前仅剩“老版 checker 不识别 ` ```codex ` 命令块”这一类历史兼容告警，正文结构、章节完整性与链接漂移检查已收口。
203. 已对第八章教程完成一轮名词解释加厚：新增“名词速览”与 6 处“名词对位讲解”，重点解释 `Retriever / Reranker / EmbeddingProvider / RetrievalHit / bridge / where / upsert / 行为不变量` 等高频术语。
204. 本轮第八章教程精修未改动任何 Retrieval Python 实现，仅增强教学解释密度与术语可读性，便于读者先建立词汇地图再读源码。
205. 已启动历史章节质量回收：优先处理第 5 章 Tool Runtime，先补齐 `运行命令 / 增量闭环验证 / 验证清单 / 常见问题 / 本章 DoD` 等缺口，并统一顶层章节标题到第 7/8 章风格。
206. 第 5 章本轮已新增“名词速览”“角色分工图”“Hook 名词对位讲解”“ChainRunner 名词对位讲解”“测试为什么重要”等解释层内容，且 `code_block_guard verify` 已通过，确认原有代码块未被删减。
207. 第 5 章复跑教程检查后，当前残留告警仍主要来自旧版 checker 不识别 ` ```codex ` 命令块创建方式；正文结构、术语密度与收尾章节已基本收口。

212. 第 2 章已完成第二轮讲解加厚：新增“名词速览”、协议数据流约束图、`domain/__init__.py` 的公共边界讲解、`schemas.py` 的成功/失败链路拆解，以及“测试为什么重要”小节。
213. 第 2 章本轮加厚已再次通过 `tutorial-quality-checker` 与 `code_block_guard` 校验（before=25, now=25），确认只追加讲解层内容，未删减原有代码块。
214. 第 3 章已完成一轮质量回收：修复 `engine/__init__.py`、`engine/application/loop.py`、`tests/unit/test_engine.py` 三处教程代码漂移，使文内代码块重新与主线源码一致。
215. 第 3 章本轮已新增“名词速览”“导出边界名词对位讲解”“为什么 Engine 不直接依赖 Tool Runtime / Model Runtime”“测试为什么重要”等解释层内容，重点加厚 `stable step key / resume_skip / backpressure / event listener` 等高频概念。
216. 第 3 章已通过 `tutorial-quality-checker` 复检；由于本轮主动修复了 3 个漂移代码块，旧基线 `code_block_guard` 校验预期失败，重建新基线后再次 verify 已通过（before=24, now=24）。
217. Engine 代码主干已开始从“单体大循环”升级为“阶段可插拔内核”：`EngineLoop` 当前保留兼容 facade，但内部已拆为顶层 pipeline（plan / execute_steps / finish）与单步 attempt pipeline（time_budget_guard / act_start / act / observe / reflect / decide）。
218. 已新增 `EngineStage` 与 `EnginePipelineContext` 两个公开类型，并支持 `pipeline_customizer`、`attempt_stage_customizer` 两种扩展入口；新增单测覆盖“顶层阶段扩展计划步骤”和“单步阶段插入自定义观测逻辑”两条路径。
219. Engine 定向回归已通过：`python -m pytest tests/unit/test_engine.py -q`（10 passed）、`python -m pytest tests/unit/test_tool_runtime_engine_integration.py tests/unit/test_observability.py -q`（9 passed）；全量 `python -m pytest -q` 因本机环境缺少 `openai` 依赖在收集阶段失败，非本轮 Engine 改造引入。
220. 已按用户反馈将臃肿的 `engine/application/loop.py` 拆分为 `domain/schemas.py`、`application/context.py`、`application/helpers.py`、`application/loop.py` 四层：类型定义、pipeline 上下文、辅助函数与运行时 facade 分离，降低单文件耦合度。
221. 本轮拆分后已完成一轮代码质检并顺手修复类型卫生问题：将模糊的 `callable` 注解收口为 `Callable[[], int]`，将 pipeline 上下文中的裸 `dict` 收口为带键值类型的字典注解。
222. 拆分后 Engine 相关回归再次通过：`python -m py_compile ...engine...` 通过，`python -m pytest tests/unit/test_engine.py tests/unit/test_tool_runtime_engine_integration.py tests/unit/test_observability.py -q` 通过（19 passed）；第三章教程现有源码块已同步到当前代码并通过 `tutorial-quality-checker` 与 `code_block_guard` 复检。
223. 已继续升级 Engine 的 plan 模型：新增 `ExecutionPlan`，将 `plan_id / revision / origin / reason / global_task / metadata / steps` 提升为计划层一等公民，不再只把计划视为“步骤列表”。
224. `PlanStep` 已补齐生产导向字段：`kind / depends_on / priority / timeout_ms / max_retry_per_step / metadata`，并支持步骤级超时与重试覆盖；`plan` 与 `finish` 事件现会显式记录 `plan_id / plan_revision / plan_origin / global_task`。
225. 已新增回归测试 `test_engine_should_record_global_task_in_plan_events`，验证 `ExecutionPlan.global_task` 会进入 `plan` 与 `finish` 事件；最新 Engine 定向回归通过（11 passed + 9 passed），第三章源码块同步后再次通过 `tutorial-quality-checker` 与 `code_block_guard` 复检。
226. 已继续升级 Engine 决策模型：`ReflectDecision` 新增 `replan` 动作、`replacement_plan` 与 `plan_update_mode`，`EngineLimits` 新增 `max_replans`，Engine 可在 reflect 阶段正式触发计划修订，而不再只会继续/重试/终止。
227. Engine 当前已支持真正的重规划链路：`_apply_replan()` 会生成修订后的 `ExecutionPlan`，继承原 `plan_id/global_task`、提升 `revision`，并把 `replan` 事件写入 trace；新增用例覆盖“替换剩余步骤”和“重规划次数超限失败”两条路径。
228. 本轮代码质检发现并修复了一个真实回归缺陷：`_stage_execute_steps()` 改成 `while` 后，`resume_skip` 分支缺少 `step_index += 1`，会导致恢复场景原地打转；修复后 Engine 回归再次通过（`test_engine.py` 13 passed，Engine 相关集成 9 passed），第三章现有源码块同步后再次通过 `tutorial-quality-checker` 与 `code_block_guard` 复检。
- 2026-03-08??? Engine ???????? Engine ?? 13 passed?Engine ???? 9 passed???????????????? context.plan_steps?????????????????????????? plan mutation API?
- 2026-03-08?Engine ???????????1?`depends_on / priority` ???? `schedule_execution_plan(...)` ???????2?`EnginePipelineContext` ?? `replace_plan_steps()/append_plan_steps()`??? plan mutation??? `current_plan` ? `plan_steps` ???????Engine ?? 15 passed????? 9 passed????????????????????
- 2026-03-08?Engine ?????????? `ExecutionPlan.success_criteria / constraints / risk_level / audit`????????? `plan`?`replan`?`finish` ???`build_replanned_plan(...)` ????????????????`test_engine.py` 17 passed?Engine ???? 9 passed??????????????????
- 2026-03-08?Engine ???????? replan ?????????? replacement plan ????? `risk_level` ? `audit.created_by` ?????????????????? `model_fields_set` ????????????????????????????? Engine ?? 18 passed????? 9 passed?
- 2026-03-08?????????? Engine ???????????? `pipeline engine + ExecutionPlan + replan + PlanAudit`??????? PASS???????????? `code_block_guard` ????????????????? verify PASS?before=23, now=23??
- 2026-03-08???????????????? `helpers.py` ? `loop.py` ??????????/????????? `test_engine.py` ?????????????tutorial-quality-checker PASS??????? code_block_guard verify PASS?before=23, now=23??
