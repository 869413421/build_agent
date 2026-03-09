# 框架核心接口约束

本文档固定框架接口，避免后续会话漂移。

## 核心入口

1. `Agent.arun(task_input, **options) -> AgentResult`
2. `Agent.run(task_input, **options) -> AgentResult`
3. `AgentApp.register_model(name, runtime) -> None`
4. `AgentApp.register_tools(tools) -> None`
5. `AgentApp.register_memory(name, runtime) -> None`
6. `AgentApp.register_retrieval(name, runtime) -> None`
7. `AgentApp.create_agent(...) -> Agent`
8. `AgentRuntime.arun(request) -> AgentResult`
9. `AgentRuntime.run(request) -> AgentResult`
10. `EngineLoop.run(state, plan_fn, act_fn, reflect_fn=None, context=None) -> AgentState`
11. `EngineLoop.arun(state, plan_fn, act_fn, reflect_fn=None, context=None) -> AgentState`
12. `ModelRuntime.generate(model_request, **kwargs) -> ModelResponse`
13. `ToolRuntime.execute(tool_call, principal) -> ToolResult`
14. `ContextEngineeringRuntime.build_bundle(...) -> ContextBundle`
15. `RetrievalRuntime.search(query) -> RetrievalResult`
16. `MemoryRuntime.write(request) -> MemoryWriteResult`
17. `MemoryRuntime.read(query) -> MemoryReadResult`
18. `EvaluatorRuntime.evaluate(request) -> EvaluationResult`
19. `SafetyRuntime.check_input(request) -> SafetyDecision`
20. `SafetyRuntime.check_tool_call(request) -> SafetyDecision`
21. `SafetyRuntime.check_output(request) -> SafetyDecision`

## 核心类型

1. `TaskInput`
2. `AgentState`
3. `AgentMessage`
4. `FinalAnswer`
5. `ToolSpec`
6. `ToolCall`
7. `ToolResult`
8. `ModelRequest`
9. `ModelResponse`
10. `ExecutionEvent`
11. `AgentConfig`
12. `AgentRunRequest`
13. `AgentResult`
14. `AgentAppTool`
15. `FrameworkResult`
16. `EvaluationRequest`
17. `StateSnapshot`
18. `ConfigVersion`
19. `ErrorInfo`
20. `ContextBundle`
21. `ExecutionPlan`
22. `PlanStep`
23. `PlanAudit`
24. `ReflectDecision`
25. `Document`
26. `Citation`
27. `RetrievalQuery`
28. `RetrievalResult`
29. `Retriever`
30. `Reranker`
31. `EmbeddingProvider`
32. `MemoryWriteRequest`
33. `MemoryWriteResult`
34. `MemoryReadQuery`
35. `MemoryReadResult`
36. `MemoryRecord`
37. `EvaluationResult`
38. `EvaluationScore`
39. `EvaluationRubric`
40. `TrajectorySummary`
41. `SafetyCheckRequest`
42. `SafetyDecision`
43. `SafetyRule`
44. `SafetyAuditRecord`
45. `SafetyReviewer`

## 必含字段约束

1. 协议对象必须有 `protocol_version`
2. 执行事件必须有 `trace_id/run_id/step_id`
3. 错误对象必须有 `error_code/error_message/retryable`
4. 工具执行必须有 `tool_call_id`（用于幂等去重）
5. 运行态必须可追踪隔离键：`tenant_id`（可选）/`user_id`（可选）/`session_id`（必选）
6. 关键运行时版本必须可见：`config_version`、`model_version`、`tool_version`、`policy_version`
7. 检索结果必须暴露 `backend_name`、`retriever_version`、`reranker_version`
8. 执行计划必须至少暴露 `plan_id`、`revision`、`origin`、`global_task`、`steps`
9. 步骤对象若声明了 `depends_on`、`priority`，执行调度必须真实生效，不能只作为展示字段
10. 反思决策若返回 `replan`，必须携带可审计的计划修订信息，不能只替换内存中的剩余步骤列表
11. Memory 读写必须显式带 `tenant_id/user_id/session_id` 等隔离键，不能从运行态隐式兜底
12. Memory 语义查询若落到向量库，必须能回填为结构化 `MemoryRecord`
13. Evaluator 评估输出必须结构化，至少暴露 `verdict / total_score / scores / summary`
14. LLM Judge 若接入模型能力，必须统一走 `ModelRuntime`，不能在 Evaluator 内直接耦合具体模型 SDK
15. 轨迹评估必须能消费 `ExecutionEvent` 序列，不能只看最终答案
16. Safety 审查输出必须结构化，至少暴露 `allowed / action / stage / policy_version`
17. Safety reviewer 必须可插拔；后续替换成 LLM 或第三方 API 时不得改变 `SafetyDecision` 契约

## Safety 特别约束

1. Safety 首版保持独立 runtime，不直接修改 `EngineLoop.run/arun` 公共签名
2. Safety 首版必须同时覆盖 `input / tool / output` 三个阶段
3. `ToolRuntime` 的安全接入应通过 hook 完成，避免把策略逻辑硬编码进工具执行器
4. 输出安全降级后仍必须返回合法 `FinalAnswer`，不能破坏前端与评估侧的结构化消费契约
5. 审计证据默认脱敏；reviewer 不得把明文敏感字段直接写入 audit / trace / log

## Engine 特别约束

1. Engine 主链路固定为 `plan -> act -> observe -> reflect -> update -> finish`
2. `reflect` 不能省略；默认实现至少要能区分 `continue / retry / abort`
3. `replan` 属于正式计划修订动作，必须体现在 `ExecutionPlan.revision` 与事件审计字段里
4. 恢复跳过必须基于稳定步骤键，而不是步骤索引
5. `update` 是步骤提交点；只有走到这里，这一步才算真正完成

## Agent 特别约束

1. 用户主推荐入口固定为 `AgentApp`，`Agent` 保留为轻量直用路径与继承扩展入口。
2. `AgentApp` 只负责注册共享能力与创建 `Agent`，不得直接承担 `run/arun` 执行职责。
3. `AgentApp.create_agent(...)` 必须返回 `Agent`，不得再引入新的执行门面类型。
4. `AgentApp.register_tools(...)` 负责登记全局工具池；`create_agent(..., allowed_tools=[...])` 只负责选择当前 agent 可用的授权工具子集。
5. `AgentRuntime` 现已接通 `allowed_tools` 与 `memory` 主链路：
   `allowed_tools` 会经模型工具规划进入 `ToolRuntime`，
   `memory` 会执行“前置读取注入 + 最终答案写回”闭环。
6. `AgentApp.register_memory(...)` 首版只接受具备 `read(...) / write(...)` 的 memory runtime，不接受裸 store；若后续要支持 store，必须在应用层先包装成 runtime 再注册。
7. `Agent` 必须保持可继承，至少保留 `_build_runtime / _build_request / _before_run / _after_run / _on_error / _get_capabilities / _get_context` 这些稳定扩展点。
8. `AgentRuntime` 是正式编排层，负责把 Safety、Engine、Context、Model、Tool、Evaluator 等组件收口成统一运行链路。
9. `AgentRuntime` 必须支持注入自定义 `EngineLoop`；允许用户替换默认执行机制，但不得破坏 `AgentState / ExecutionPlan / FinalAnswer` 等稳定协议。
10. CLI、API 等应用层入口应优先建立在 `AgentApp` 或其创建出的 `Agent` 之上，不得重新实现一套独立装配逻辑。

## Evaluator 特别约束

1. `EvaluatorRuntime` 首版保持独立 runtime，不直接侵入 `EngineLoop` 主链路
2. Evaluator 首版必须同时支持 `output / trajectory / combined` 三种模式
3. 规则评估与 LLM judge 评估都必须能产出统一 `EvaluationResult`
4. `compare(...)` 的输入必须是结构化评估结果，不能直接比较原始运行记录

## 变更规则

1. 任一接口签名变更，必须同步更新本文档与测试。
2. 任一新增类型必须补用途、字段、示例。
3. 禁止 API 层绕过框架层直接写业务逻辑。


