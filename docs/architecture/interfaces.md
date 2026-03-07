# 框架核心接口约束

本文档固定框架接口，避免后续会话漂移。

## 核心入口

1. `Framework.run(task_input, session_id) -> FrameworkResult`
2. `Engine.loop(state, limits) -> AgentState`
3. `ModelRuntime.generate(model_request, **kwargs) -> ModelResponse`
4. `ToolRuntime.execute(tool_call, principal) -> ToolResult`
5. `ContextBuilder.build(state, budget) -> ContextBundle`
6. `Evaluator.score(run_record) -> EvalReport`

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
17. `Document`
18. `Citation`
19. `RetrievalQuery`
20. `RetrievalResult`
21. `Retriever`
22. `Reranker`
23. `EmbeddingProvider`

## 必含字段约束

1. 协议对象必须有 `protocol_version`
2. 执行事件必须有 `trace_id/run_id/step_id`
3. 错误对象必须有 `error_code/error_message/retryable`
4. 工具执行必须有 `tool_call_id`（用于幂等去重）
5. 运行态必须可追踪隔离键：`tenant_id`（可选）/`user_id`（可选）/`session_id`（必选）
6. 关键运行时版本必须可见：`config_version`、`model_version`、`tool_version`、`policy_version`
7. 检索结果必须暴露 `backend_name`、`retriever_version`、`reranker_version`

## 变更规则

1. 任一接口签名变更，必须同步更新本文档与测试。
2. 任一新增类型必须补用途、字段、示例。
3. 禁止 API 层绕过框架层直接写业务逻辑。


