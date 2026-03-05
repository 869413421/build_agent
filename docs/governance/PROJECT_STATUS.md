# 项目状态（交接单一事实源）

## 当前阶段

- 阶段：仓库结构重构完成（`agent_forge` 命名、`src/` 布局、组件分层落地）
- 日期：2026-03-02

## 已完成组件

- [x] Protocol
- [x] Engine（loop）
- [x] Model Runtime（LLM Adapter）
- [ ] Tool Runtime（API Adapter，代码已完成，教程待审核后编写）
- [ ] Observability
- [ ] Context Engineering
- [ ] Retrieval
- [ ] Memory
- [ ] Evaluator
- [ ] Safety Layer

## 进行中组件（唯一）

- Tool Runtime（API Adapter）（代码与测试已落地，等待教程小步）

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

- 若本步审核通过，进入第五章教程撰写与文档同步（不改代码主干）。

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
