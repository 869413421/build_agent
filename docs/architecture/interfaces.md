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
8. `Evaluator.score(run_record) -> EvalReport`

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
12. `EvalReport`
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

## Engine 特别约束

1. Engine 主链路固定为 `plan -> act -> observe -> reflect -> update -> finish`
2. `reflect` 不能省略；默认实现至少要能区分 `continue / retry / abort`
3. `replan` 属于正式计划修订动作，必须体现在 `ExecutionPlan.revision` 与事件审计字段里
4. 恢复跳过必须基于稳定步骤键，而不是步骤索引
5. `update` 是步骤提交点；只有走到这里，这一步才算真正完成

## 变更规则

1. 任一接口签名变更，必须同步更新本文档与测试。
2. 任一新增类型必须补用途、字段、示例。
3. 禁止 API 层绕过框架层直接写业务逻辑。


