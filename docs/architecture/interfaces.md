# 框架核心接口约束

本文档固定框架接口，避免后续会话漂移。

## 核心入口

1. `Framework.run(task_input, session_id) -> FrameworkResult`
2. `EngineLoop.run(state, plan_fn, act_fn, reflect_fn=None, context=None) -> AgentState`
3. `EngineLoop.arun(state, plan_fn, act_fn, reflect_fn=None, context=None) -> AgentState`
4. `ModelRuntime.generate(model_request, **kwargs) -> ModelResponse`
5. `ToolRuntime.execute(tool_call, principal) -> ToolResult`
6. `ContextEngineeringRuntime.build_bundle(...) -> ContextBundle`
7. `RetrievalRuntime.search(query) -> RetrievalResult`
8. `MemoryRuntime.write(request) -> MemoryWriteResult`
9. `MemoryRuntime.read(query) -> MemoryReadResult`
10. `EvaluatorRuntime.evaluate(request) -> EvaluationResult`
11. `SafetyRuntime.check_input(request) -> SafetyDecision`
12. `SafetyRuntime.check_tool_call(request) -> SafetyDecision`
13. `SafetyRuntime.check_output(request) -> SafetyDecision`

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
11. `FrameworkResult`
12. `EvaluationRequest`
13. `StateSnapshot`
14. `ConfigVersion`
15. `ErrorInfo`
16. `ContextBundle`
17. `ExecutionPlan`
18. `PlanStep`
19. `PlanAudit`
20. `ReflectDecision`
21. `Document`
22. `Citation`
23. `RetrievalQuery`
24. `RetrievalResult`
25. `Retriever`
26. `Reranker`
27. `EmbeddingProvider`
28. `MemoryWriteRequest`
29. `MemoryWriteResult`
30. `MemoryReadQuery`
31. `MemoryReadResult`
32. `MemoryRecord`
33. `EvaluationResult`
34. `EvaluationScore`
35. `EvaluationRubric`
36. `TrajectorySummary`
37. `SafetyCheckRequest`
38. `SafetyDecision`
39. `SafetyRule`
40. `SafetyAuditRecord`
41. `SafetyReviewer`

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

## Evaluator 特别约束

1. `EvaluatorRuntime` 首版保持独立 runtime，不直接侵入 `EngineLoop` 主链路
2. Evaluator 首版必须同时支持 `output / trajectory / combined` 三种模式
3. 规则评估与 LLM judge 评估都必须能产出统一 `EvaluationResult`
4. `compare(...)` 的输入必须是结构化评估结果，不能直接比较原始运行记录

## 变更规则

1. 任一接口签名变更，必须同步更新本文档与测试。
2. 任一新增类型必须补用途、字段、示例。
3. 禁止 API 层绕过框架层直接写业务逻辑。


