# 会话交接检查清单

在每次会话结束前逐项确认：

1. [x] 本次是否只实现了一个组件（Engine）
2. [x] 是否提交了对应测试（`tests/test_engine.py`）
3. [x] 是否提交了对应教程内容（`docs/tutorials/03-从0到1工业级Agent框架打造-第三章-Engine循环-反思机制与生产约束.md`）
4. [x] 是否更新 `docs/governance/PROJECT_STATUS.md`
5. [x] 是否更新相关规则/架构文档（生产级 DoD 与约束已加严）
6. [x] 是否明确写出“下一步唯一任务”（Model Runtime）
7. [x] 是否已通知用户审核

---

## 会话补充（2026-03-02）

1. [x] 本次是否保持“小步交付”（仅推进第二章教程与 chapter_02 快照）
2. [x] 是否同步了教程与代码快照一致性（chapter_02 与主线 protocol 对齐）
3. [x] 是否完成了可运行验证（chapter_02 测试 + 主线协议测试）
4. [x] 是否更新 `docs/governance/PROJECT_STATUS.md`
5. [x] 是否等待用户审核后再进入下一步
6. [x] 是否移除教程中的本机绝对路径并补齐主线同步命令
7. [x] 是否确保教程命令跨 shell 可直接执行（避免仅 Bash 语法）
8. [x] 是否在复杂章节提供术语白话卡片与阅读路径（先最小可跑再深挖）
9. [x] 是否提供真实调用打通入口（不仅 stub）并给出手动线上执行命令


10. [x] 是否已回补 01~04 章创建目录与文件命令（Bash + PowerShell，含文件创建而非仅目录）


11. [x] 第一章已按黄金标准重构（先面后点、代码讲解、分步创建命令、可复制运行）

12. [x] 第二章文件前置创建命令代码块已补齐（每个文件段前 bash + powershell）
13. [x] 第三、第四章文件前置创建命令代码块已补齐（每个文件段前 bash + powershell）

14. [x] 第02~04章承接复制步骤已补齐（开篇先复制上一章快照）
15. [x] CLI 子命令修复已同步（主线+chapter_01代码与教程一致）


16. [x] 已补充第一章 CLI 子命令修复后的教程验证闭环（预期输出 + uv sync 刷新步骤）

17. [x] 已完成教程架构从‘章节快照双轨’迁移到‘主线单轨 + Tag 回放索引’。
18. [x] 已清理 01~04 章快照路径引用并新增章节索引文件。
19. [ ] 剩余 6 个受 ACL 保护的 pytest 缓存目录待具备文件所有权权限后手动删除。

20. [x] 已完成第一章教程去噪（仅措辞与可读性修复，未删减非噪音内容）。

21. [x] 第二章创建文件命令已修复（路径正确 + 代码块渲染正常）。

22. [x] 第三、第四章已完成本轮清理：第四章空命令块已修复并补齐代码块命令；第三章已复核通过，无需改动。

23. [x] 第一章已按新模板/新标准完成增量优化：结构补齐、命令区统一、PowerShell 等价命令补全、预期输出修正。
24. [x] 第二章已按新模板/新标准完成增量优化：结构补齐、运行命令双端一致、闭环验证补全、文案瑕疵修正。
25. [x] 第三章已按新模板/新标准完成增量优化：结构补齐、运行命令双端一致、闭环验证补全、DoD 与预告完善。
26. [x] 第三章导出文件步骤已修复与主线一致（导入路径与讲解文案对齐真实代码）。
27. [x] 已创建教程文章质检 Skill（tutorial-quality-checker）并完成脚本可用性验证。
28. [x] 第四章已完成缺失段落补齐并通过文章检查 Skill 校验。
29. [x] 文章检查 Skill 已支持代码漂移检查并完成第四章实测。
30. [x] 第四章代码漂移已修复，文章检查 Skill 复检通过（含 BOM 兼容）。
31. [x] 第四章环境准备与 .env 配置方式已落地，文章检查 Skill 复检通过。
32. [x] 第四章 `model_runtime` 相关代码已补齐为教程内全量可复制版本（含 `__init__.py`、`stub.py`、adapter/runtime/测试全文），并通过文章检查 Skill（含代码漂移检查）。
33. [x] 第四章已将缺失的 `__init__.py` 前置到对应步骤，且《黄金标准》《章节模板》已新增“包目录必须同步创建并展示 `__init__.py`”硬约束，避免后续再次遗漏。
34. [x] 已修复 `.env` BOM 导致的环境变量读取失败：代码层兼容 `utf-8-sig`，教程层改为无 BOM PowerShell 写法，并补充 BOM 失败场景排查命令。
35. [x] 已修正 `response_format` 过于刚性的实现：支持通用透传 `response_format`，并在服务端不支持 `json_schema` 时自动降级 `json_object`；单测与第四章教程同步完成。
36. [x] 已将 DeepSeek 教学脚本迁移到 `examples/model_runtime/deepseek_demo.py`，并移除 `apps` 下同名脚本；第四章路径与命令已同步。
37. [x] 已按用户要求更新 `README.md`，新增课程索引表（01~04 章节链接 + 05~14 占位状态）。
38. [x] 已完成 Model Runtime 流式能力实现（`stream_generate` + 结构化流事件 + hooks + 失败边界）。
39. [x] 已新增并通过流式单测 `tests/unit/test_model_runtime_stream.py`，全量回归 `uv run pytest -q` 通过（23 passed）。
40. [x] 已按“先代码后教程”更新第4章并保留原有内容不删减，新增重组主线入口。
41. [x] `examples/model_runtime/deepseek_demo.py` 已支持 `--mode non-stream|stream|both`，可真实走通 DeepSeek 非流式与流式两条调用链。
42. [x] 已新增 `tests/unit/test_deepseek_demo.py` 并通过回归，示例脚本核心函数具备自动化保护。
43. [x] 第四章 `deepseek_demo.py` 对应教程代码与运行命令已同步双链路版本（含 Bash/PowerShell），且未删除既有教程内容。
44. [x] `ModelRuntime.generate` 已支持 `hooks`（before/after），非流式与流式观测语义对齐。
45. [x] 已新增非流式 hooks 回归测试并通过（`test_generate_should_call_hooks_for_non_stream`）。
46. [x] 第四章教程已按读者视角从0到1整章重写，移除补丁式前言，主线结构对齐模板（目标/架构/前置/步骤/命令/验证/问题/DoD/预告）。
47. [x] 第四章所有关键“文件：path”代码块已与主线文件重新同步，并通过代码一致性检查（无代码漂移）。
48. [x] 第四章乱码已修复（UTF-8 原文恢复），不再使用会污染中文的写入路径。
49. [x] 第四章已从章节标题直接进入读者正文，移除“重组说明”前置段，阅读顺序改为从0到1主线学习。

## 会话补充（2026-03-05）

50. [x] 已按 `publish-grade-article-auditor` 审核并优化第一章，且优化策略为“主动改文档而非仅建议”。
51. [x] 已执行代码块零删减校验：优化前 inventory 与优化后 verify 均完成，结果通过（未删除原有代码块）。
52. [x] 第一章已补齐主要代码段的深度讲解（主流程拆解、成功/失败例子、流程图/时序图、工程取舍与边界）。
53. [x] 第一章已新增“环境准备与缺包兜底步骤（可复制）”，满足教程可执行闭环要求。
54. [x] 已更新 `docs/governance/PROJECT_STATUS.md` 并等待用户审核。
55. [x] 已根据用户反馈修复第一章 Mermaid 语法兼容问题，消除 `Syntax error in text` 报错。
56. [x] 已将 Mermaid 11.12.0 兼容约束写入教程黄金标准、章节模板与 AI 执行护栏，后续优化默认遵循该规则。
57. [x] 已使用 `publish-grade-article-auditor` 完成第 02~05 章审核优化（保守精简重复叙述，不删代码块）。
58. [x] 第 02~05 章代码零删减校验全部通过（inventory + verify）。
59. [x] 第 04~05 章已补齐跨环境运行命令（Bash + PowerShell）与 `python` 兜底路径，工程可执行闭环已增强。
60. [x] 第 05 章已修正下一章承接文案为 Observability，与组件路线图保持一致。
61. [x] 已按用户要求再次优化第 04 章，并补齐主要代码段深度讲解（主流程拆解 + 成功/失败例子 + 图示 + 工程取舍/边界）。
62. [x] 第 04 章本轮代码零删减校验通过：`before=75, now=80`。
63. [x] 已同步更新 `docs/governance/PROJECT_STATUS.md` 记录本轮优化与校验结果，等待用户审核。


## 会话补充（2026-03-03）

50. [x] 已完成 Tool Runtime 组件代码实现（注册/校验/权限/幂等/超时/错误映射/记录）。
51. [x] 已实现两个示例工具（Tavily 搜索 + Python 数学表达式工具）。
52. [x] 已完成 Tool Runtime 单测与 Engine 零侵入集成测试，并通过离线回归（36 passed）。
53. [ ] 第五章教程尚未开始（按用户要求先验收代码后再规划教程）。
54. [x] 已更新 `docs/governance/PROJECT_STATUS.md`。
55. [x] 已通知用户当前可进入“代码审核”步骤。
56. [x] Tool Runtime 已补齐 `execute_async`、hooks 与 chain 机制，并通过新增测试验证。
57. [x] 已修复 Tool Runtime 前置错误路径未触发 `on_error` hook 的问题。
58. [x] 全量回归更新为 39 passed（`uv run --no-sync pytest -q`）。
59. [x] 已完成 Tool Runtime 工程化重构：异步执行与链式编排从门面类拆分为独立服务对象（Executor/ChainRunner/HookDispatcher）。
60. [x] 已按约束补齐 Tool Runtime 主流程分步注释（含执行与链式编排）。
61. [x] 已新增异步批量工具执行接口 `execute_many_async` 并补全测试。
62. [x] 已为 tool_runtime_demo 增加完整单测覆盖（5个新增用例）。
63. [x] 已为 tool_runtime_demo 增加工具链示例与对应测试（成功链路 + 失败短路）。
64. [x] 已将“参数级注释 + 每个方法注释全覆盖”写入 AI 任务硬约束并在本次 Tool Runtime 代码执行。
65. [x] 已补齐 Tool Runtime 主代码方法级注释并完成全量回归（48 passed）。
66. [x] 已修复第五章 Mermaid 11.12.0 架构图语法错误，并同步“节选代码必须给完整文件提醒”规则到模板与黄金标准。
67. [x] 已按用户反馈增强第五章代码讲解：通俗化、举例化，并补图（含时序图）。
68. [x] 已将“通俗讲解+举例+图示+仅追加不删减”加入教程黄金法则并完成第01~04章增量升级。
69. [x] 已修复第五章缺口：补 ChainRunner 代码示例、增强第5/6步讲解、补 demo 脚本段落。
70. [x] 已新增硬约束：教程禁止补丁式写法，新增内容必须自然融合正文主线。
71. [x] 已完成第01~04章“自然融合式”文档优化：第02/03章附录式标题改为主线化“深入理解”标题，第04章补充同风格“深入理解”章节；不删减任何原有内容与代码。
72. [x] 已完成第01~04章“深入理解”章节位置重排：从文末后置追加改为正文前半段前置讲解（在主线改动范围/实施步骤前），保证阅读顺序自然。
73. [x] 已完成第五章 `chain_runner.py` 讲解增强：补齐主流程拆解、成功/失败例子、流程图+时序图，以及工程取舍与边界说明。
74. [x] 已将“主要代码讲解需达到 `chain_runner.py` 级别”写入黄金法则、章节模板与 AI 执行硬约束，后续章节按该标准统一执行。
75. [x] 已创建并验证新技能 `publish-grade-article-auditor`（出版级审核+主动优化+代码零删减校验脚本）。
76. [x] 已修复技能加载报错：`.agents/skills/publish-grade-article-auditor/SKILL.md` 改为 UTF-8 无 BOM（frontmatter 从首字节 `---` 开始），并同步将 `.agents/skills/tutorial-quality-checker/SKILL.md` 统一为 UTF-8 无 BOM。
77. [x] Re-optimized Chapter 05 docs: added environment fallback, run commands, verification checklist, and FAQ supplement; original code blocks kept intact.
78. [x] Code-block guard verification completed for Chapter 05: `before=49, now=56, PASS`.

## 会话补充（2026-03-05 Observability）

79. [x] 本次仅实现一个新组件（Observability），未跨组件并行开发。
80. [x] 已提交 Observability 对应代码与测试（`src/agent_forge/components/observability/`、`tests/unit/test_observability.py`）。
81. [x] 已完成 Engine 可选事件监听接入并验证监听器异常不影响主流程。
82. [x] 已完成 ToolRuntime hook 接入并验证 trace/replay 链路可用。
83. [x] 已完成全量回归：`uv run --no-sync pytest -q`（53 passed）。
84. [x] 已新增第六章教程并与代码路径同步。
85. [x] 已更新 `docs/governance/PROJECT_STATUS.md` 与 `README.md` 课程索引状态。
86. [x] 已完成 Observability 质检问题修复：工具观测上下文改为任务级隔离（`ContextVar`），避免并发串 run。
87. [x] 已补齐失败工具回放：错误结果也会进入 replay，并在 ToolRuntime records 持久化。
88. [x] 已新增并发隔离与失败回放回归测试，最新全量回归通过（55 passed）。
89. [x] 已按用户反馈重构第六章教程：从占位式说明改为完整可运行代码讲解，结构按模板补齐。
90. [x] 第六章已补齐“环境准备与缺包兜底步骤”，并提供 Bash/PowerShell 双命令。
91. [x] 第六章已通过教程结构硬约束检查：`python .agents/skills/tutorial-quality-checker/scripts/check_tutorial_markers.py --file docs/tutorials/06-从0到1工业级Agent框架打造-第六章-Observability-可观测与回放闭环.md`。
92. [x] 第六章已通过代码块零删减校验：`code_block_guard verify` 结果 `before=33, now=33, PASS`。
93. [x] 已根据用户反馈补齐第六章“术语白话卡片”，先讲概念再讲代码。
94. [x] 已补齐第六章真实成功/失败案例（输入输出级），用于对照 runtime 与 hook 行为。
95. [x] 已补齐第六章 runtime 分步走读（1/2/3/4）与 hook 踩坑说明，强化失败推演与工程边界。
96. [x] 第六章本轮复检通过：`tutorial-quality-checker` PASS。
97. [x] 已修复第六章创建命令顺序：先建目录再建文件，且按“讲一个创建一个”组织。
98. [x] 已补齐第六章相关 `__init__.py` 创建命令，避免手把手跟做时漏建包入口文件。
99. [x] 已将第六章创建命令从“集中在第 2 步”改为“第 3~9 步就地创建”，实现讲一步建一步。
100. [x] 第六章创建顺序已统一为：先目录 -> 再 `__init__.py` -> 再目标文件。
101. [x] 重排后已复检通过：`tutorial-quality-checker` PASS。
102. [x] 第六章命令块格式已统一为 ` ```codex `（按用户要求）。
103. [x] 第六章文档已重建并修复编码显示问题，中文可读性恢复正常。
104. [x] 已修复第六章“内容全部丢失”问题：占位代码块全部恢复为完整源码与测试代码。
105. [x] 第六章命令块维持 ` ```codex ` 统一格式，且创建顺序符合“目录 -> `__init__.py` -> 目标文件”。
106. [x] 修复后再次通过教程结构检查：`tutorial-quality-checker` PASS。
107. 已修复第六章代码块与正文包裹错位：补齐所有缺失的代码块结束栅栏，正文段落恢复为普通 Markdown。
108. 修复后复检结果：代码栅栏配对正常（FENCES_BALANCED），教程结构检查通过（PASS）。
109. [x] 已完成第六章对标第五章的深度升级：关键代码段讲解从简要说明提升为主流程+成功/失败案例+工程取舍。
110. [x] 第六章升级后校验通过：code_block_guard verify PASS（before=19, now=20）、教程结构 PASS、代码栅栏 FENCES_BALANCED。
111. [x] 已清理第六章中文乱码（问号污染）并替换为可读中文讲解，7 段污染区域全部修复。
112. [x] 乱码修复后复检通过：问号计数=0，教程结构 PASS，代码块零删减 PASS。
113. [x] 已修正文档概念歧义：Engine 侧为 event_listener 回调注入，不是 Engine 自身方法 engine_event_listener。
114. [x] 已新增并验证第六章 examples 脚本：examples/observability/observability_demo.py（成功+失败工具路径与 Engine 路径均可观测）。
115. [x] 第六章已补齐 observability/domain/application/infrastructure 四个 __init__.py 的完整代码与命令。
116. [x] 第五章已自然补充 	est_tool_runtime.py 步骤（命令+完整代码+讲解），不再出现按教程执行缺失文件。
117. [x] 第五章已补齐 conftest.py 教学步骤并与 test_tool_runtime.py 顺序对齐，消除 FakeTavilyClient 缺失问题。
118. [x] 第五章已补齐 tests 包初始化文件教学步骤，避免 test 包导入报错。
119. [x] 已完成 failed-tool replay 空记录兼容修复（hooks error-event fallback）并新增单测覆盖。
120. [x] 第六章已同步 loop.py 变更说明与 test_observability 失败排查说明。
121. [x] 已落地 Context Engineering 组件代码（runtime/policy/hook/schema/estimator）并统一导出。
122. [x] 已新增 context engineering 单测 6 条并通过（tests/unit/test_context_engineering.py）。
123. [x] 已执行全量回归：uv run --no-sync pytest -q（61 passed）。
124. [x] 已完成 Context Engineering 质检修复：request.tools 保留语义、citations 真实入模、mandatory message 极限预算截断边界已修正。
125. [x] 已将 context engineering 单测扩充至 9 条并通过（tests/unit/test_context_engineering.py）。
126. [x] 已执行修复后全量回归：uv run --no-sync pytest -q（64 passed）。
127. [x] 已完成 Context Engineering 代码注释/docstring 中文化，并回归验证通过（64 passed）。
128. [x] 已完成二轮质检修复：适配器层屏蔽内部 extra 字段透传（context_budget_report/citations/tools）。
129. [x] 已新增 `test_adapter_should_not_forward_internal_context_extras` 回归用例并通过。
130. [x] 已执行最新全量回归：uv run --no-sync pytest -q（65 passed）。
131. [x] 已完成第七章教程正文编写：`docs/tutorials/07-从0到1工业级Agent框架打造-第七章-ContextEngineering-上下文编排与预算治理.md`。
132. [x] 第七章教程已补齐 `Context Engineering` 的主流程说明、完整源码、测试代码、失败模式与 DoD。
133. [x] 第七章教程命令块已统一使用 ` ```codex `，并按“目录 -> __init__.py -> 目标文件”的顺序写入。
134. [x] `README.md` 课程索引已更新，第 07 章状态改为已完成并补齐链接。
135. [x] `docs/governance/PROJECT_STATUS.md` 已同步记录本轮教程交付与索引更新。
136. [x] 已新增第七章 examples 示例：`examples/context_engineering/context_engineering_demo.py`。
137. [x] 已新增第七章示例测试：`tests/unit/test_context_engineering_demo.py`。
138. [x] examples 目录保持非包用法，已删除多余 `__init__.py`，示例测试改为按文件路径加载脚本。
139. [x] 第七章教程已追加 examples 主线步骤、完整示例代码与退化路径讲解。
140. [x] 最新全量回归已通过：`uv run --no-sync pytest -q`（67 passed）。
141. [x] 已完成第七章教程精修一轮：重点加厚 `policies.py`、`runtime.py`、`hooks.py` 三段讲解，补齐主流程时间线、Mermaid 图、成功/失败链路、工程取舍与边界说明。
142. [x] 已修复第七章本轮新增讲解段落的中文编码污染，问号计数已清零（`???=0`，`??=0`）。
143. [x] 第七章本轮精修已通过代码块零删减校验：`code_block_guard verify` PASS（before=40, now=43）。
144. [x] 已完成第七章测试讲解二次加厚：新增“逐条读懂这些测试到底在证明什么”，覆盖预算充足、旧历史裁剪、tools 优先级、citations 入模、Hook 集成、request.tools 保留与极限预算边界。
145. [x] 已完成第七章 example 测试讲解二次加厚：新增“这两条 example 测试分别锁什么”，明确 example 测试与单元测试的不同职责。
146. [x] 第七章二次精修已再次通过代码块零删减校验：`code_block_guard verify` PASS（before=40, now=44），问号污染复检继续为 0。
147. [x] 已完成第八章 Retrieval 代码落地：新增 `domain/application/infrastructure` 分层与统一导出入口。
148. [x] 已完成 Retrieval 通用抽象：`Retriever / Reranker / EmbeddingProvider` 协议与 `RetrievalQuery / RetrievalResult / RetrievedDocument / RetrievedCitation` 标准类型已落地。
149. [x] 已完成 Retrieval 基线实现：`InMemoryRetriever` 与 `NoopReranker` 可离线运行，不锁死向量库与重排技术。
150. [x] 已完成真实向量库适配示例：`ChromaRetriever` 通过注入式 `EmbeddingProvider` 接入，且缺依赖时给出清晰报错。
151. [x] 已新增 Retrieval 单测：`tests/unit/test_retrieval.py`、`tests/unit/test_retrieval_chroma.py`。
152. [x] 已更新 `pyproject.toml` 可选依赖组：新增 `retrieval-chroma`，主依赖未被向量库绑定。
153. [x] 已更新 `docs/architecture/interfaces.md`，补充 Retrieval 核心接口与版本追踪要求。
154. [x] 已执行最新全量回归：`uv run --no-sync pytest -q`（77 passed）。
155. [x] 已新增 Retrieval 示例：`examples/retrieval/retrieval_demo.py`，同时展示可离线基线路径与真实向量库路径。
156. [x] 已新增 Retrieval 示例测试：`tests/unit/test_retrieval_demo.py`。
157. [x] Chroma 示例路径在缺少可选依赖时已支持可解释降级，不会让示例脚本直接崩溃。
158. [x] 已执行新增示例后的最新全量回归：`uv run --no-sync pytest -q`（79 passed）。
159. [x] 已完成 Retrieval 质检修复：`ChromaRetriever` 会把 `RetrievalFilters` 下推为 `where` 条件，修复跨后端过滤语义不一致问题。
160. [x] 已完成 Retrieval 质检修复：`ChromaRetriever` 对 metadata 做标量类型收口，遇到不兼容类型会明确报错。
161. [x] 已增强 Retrieval 示例韧性：Chroma 路径写入/查询异常也会返回可解释降级结果。
162. [x] 已新增对应回归测试，覆盖 `where` 条件下推、metadata 类型校验与 Chroma 运行期失败降级。
163. [x] 已执行质检修复后的最新全量回归：`uv run --no-sync pytest -q`（82 passed）。
164. [x] 已完成第八章 Retrieval 教程正文，文件为 `docs/tutorials/08-从0到1工业级Agent框架打造-第八章-Retrieval-检索召回与引用标准化.md`。
165. [x] 第八章教程已补齐主流程讲解、双轨后端设计、真实向量库示例、examples 与三组测试代码。
166. [x] 第八章教程已遵守 `examples` 非包目录约束，未引导创建 `examples/__init__.py`。
167. [x] 已同步更新 `README.md` 与 `docs/governance/PROJECT_STATUS.md`，将第 08 章标记为已完成。
168. [x] 已为第八章教程补齐 `验证清单`、`常见问题`、`本章 DoD`、`下一章预告`。
169. [x] 已修复第八章教程尾部中文编码污染，并将文件路径改为可点击相对链接。
170. [x] 已复跑教程质量检查；当前残留告警仅来自旧版 checker 未适配 ` ```codex ` 命令块规范。
171. [x] 已为第八章教程新增“名词速览”，统一解释 `Retriever / Reranker / EmbeddingProvider / RetrievalHit / Citation Bridge / top_k / min_score / upsert / where`。
172. [x] 已在领域模型、runtime、bridge、InMemoryRetriever、ChromaRetriever、测试讲解六处追加“名词对位讲解”，降低读者第一次读源码时的术语门槛。
173. [x] 已开始历史章节质量回收，优先处理第 5 章 Tool Runtime。
174. [x] 第 5 章本轮已补齐 `运行命令 / 增量闭环验证 / 验证清单 / 常见问题 / 本章 DoD`，并追加术语地图、角色分工图与测试护栏讲解。
175. [x] 第 5 章本轮已通过 `code_block_guard verify`，确认未删减原有代码块；当前 residual 告警主要为旧版 checker 未适配 ` ```codex ` 创建命令格式。

180. 第 2 章已完成第二轮加厚：新增名词速览、协议数据流图、公共边界讲解、`schemas.py` 的成功/失败链路拆解，以及测试护栏解读。
181. 第 2 章本轮加厚已通过 tutorial-quality-checker PASS 与 code_block_guard PASS（before=25, now=25），确认未删减任何原有代码块。
182. 第 3 章已完成第一轮回收：修复 `engine/__init__.py`、`engine/application/loop.py`、`tests/unit/test_engine.py` 三处教程代码漂移，并补充名词速览、依赖方向讲解与测试护栏说明。
183. 第 3 章本轮已通过 tutorial-quality-checker PASS；旧 `code_block_guard` 基线因主动修复漂移而预期失效，重建新基线后 verify PASS（before=24, now=24）。
184. Engine 已开始做结构升级：在不破坏 `EngineLoop` 公开接口的前提下，把内部执行改成顶层 pipeline + 单步 attempt pipeline，并公开 `EngineStage`、`EnginePipelineContext` 作为扩展入口。
185. 已新增 2 条 Engine 可扩展性回归测试，验证可插入顶层阶段扩展计划步骤，以及可插入单步阶段追加自定义观测逻辑。
186. 当前 Engine 定向回归通过（10 passed + 9 passed）；全量 pytest 因环境缺少 `openai` 依赖在 collection 阶段失败，需在后续恢复完整环境后再补跑一次全量。
187. 已继续按用户要求拆分臃肿的 `loop.py`：当前 Engine 代码分为 `domain/schemas.py`、`application/context.py`、`application/helpers.py`、`application/loop.py`，其中 `loop.py` 只保留 facade 与阶段编排逻辑。
188. 本轮代码质检已完成并修复两处卫生问题：`now_ms` 注解从模糊 `callable` 收口为 `Callable[[], int]`，pipeline 上下文字段与事件写入参数从裸 `dict` 收口为显式键值类型。
189. 拆分后 Engine 相关编译与定向回归均通过（py_compile 通过，pytest 共 19 passed）；第三章现有源码块已同步并通过 tutorial-quality-checker 与 code_block_guard 复检。
190. 已继续升级 plan 为计划对象：新增 `ExecutionPlan`，并把 `global_task`、计划修订号、来源、原因和计划元数据正式纳入计划层与事件层。
191. `PlanStep` 已扩为生产导向节点：支持 `kind / depends_on / priority / timeout_ms / max_retry_per_step / metadata`，其中步骤级超时与重试覆盖已接入当前 Engine 执行逻辑。
192. 已新增 `global_task` 回归测试并通过；第三章现有源码块已再次同步到当前 Engine 代码，并通过 tutorial-quality-checker 与 code_block_guard 复检。
193. 已继续实现 `replan`：`ReflectDecision` 现支持 `replan + replacement_plan + plan_update_mode`，`EngineLimits` 新增 `max_replans`，Engine 可在 reflect 阶段正式修订后续执行计划。
194. 已新增 2 条回归测试，分别验证“reflect 触发重规划后替换剩余步骤”和“超出最大重规划次数时返回 REPLAN_LIMIT_REACHED”。
195. 本轮代码质检发现并修复一个回归 bug：`resume_skip` 分支在 `while` 循环下遗漏 `step_index += 1`，导致恢复场景卡死；修复后 Engine 单测 13 passed、Engine 相关集成 9 passed，第三章源码块已再次同步并通过教程检查。
- 2026-03-08?Engine ?????????`python -m py_compile src/agent_forge/components/engine/domain/schemas.py src/agent_forge/components/engine/application/context.py src/agent_forge/components/engine/application/helpers.py src/agent_forge/components/engine/application/loop.py tests/unit/test_engine.py`?`python -m pytest tests/unit/test_engine.py -q`?`python -m pytest tests/unit/test_tool_runtime_engine_integration.py tests/unit/test_observability.py -q`????????????? stage ????? `context.plan_steps`????? `current_plan` ???
- 2026-03-08???? Engine ???????????????? `schedule_execution_plan(...)`?? `depends_on/priority` ????? `EnginePipelineContext.replace_plan_steps()/append_plan_steps()`?????????????`python -m py_compile ...engine... tests/unit/test_engine.py`?`python -m pytest tests/unit/test_engine.py -q`?15 passed??`python -m pytest tests/unit/test_tool_runtime_engine_integration.py tests/unit/test_observability.py -q`?9 passed????? `tutorial-quality-checker` PASS?
- 2026-03-08???? Engine ??????????? `PlanAudit` ? `ExecutionPlan.success_criteria / constraints / risk_level / audit`??????????????????????/????????`python -m py_compile ...engine... tests/unit/test_engine.py`?`python -m pytest tests/unit/test_engine.py -q`?17 passed??`python -m pytest tests/unit/test_tool_runtime_engine_integration.py tests/unit/test_observability.py -q`?9 passed????? `tutorial-quality-checker` PASS?
- 2026-03-08???? Engine replan ???? bug?replacement plan ?? `risk_level`/`audit.created_by` ???????????????? `test_engine_should_inherit_risk_and_audit_creator_when_replan_omits_them`????`python -m py_compile src/agent_forge/components/engine/application/helpers.py tests/unit/test_engine.py`?`python -m pytest tests/unit/test_engine.py -q`?18 passed??`python -m pytest tests/unit/test_tool_runtime_engine_integration.py tests/unit/test_observability.py -q`?9 passed??
- 2026-03-08???????????? Engine ??????`tutorial-quality-checker` PASS?????????????????`code_block_guard inventory --out .tmp/ch03-code-inventory-v2.json` ? `verify` PASS?before=23, now=23??
- 2026-03-08?????????????? `helpers.py`/`loop.py` ???????/???????????????? PASS?????? PASS?before=23, now=23??
- [2026-03-08] 第三章完成“降认知负担精修”：补了三句话主线、生活化例子、`loop.py` 两遍阅读法、测试主线入口；文档检查通过，代码块零删减校验通过。
