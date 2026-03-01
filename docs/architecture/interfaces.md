# 框架核心接口约束

本文档固定框架接口，避免后续会话漂移。

## 核心入口

1. `Framework.run(task_input, session_id) -> FrameworkResult`
2. `Engine.loop(state, limits) -> AgentState`
3. `ModelRuntime.generate(model_request) -> ModelResult`
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
9. `ModelResult`
10. `ExecutionEvent`
11. `FrameworkResult`
12. `EvalReport`
13. `StateSnapshot`
14. `ConfigVersion`
15. `ErrorInfo`
16. `ContextBundle`
17. `Document`
18. `Citation`

## 必含字段约束

1. 协议对象必须有 `protocol_version`
2. 执行事件必须有 `trace_id/run_id/step_id`
3. 错误对象必须有 `error_code/error_message/retryable`
4. 工具执行必须有 `tool_call_id`（用于幂等去重）

## 变更规则

1. 任一接口签名变更，必须同步更新本文档与测试。
2. 任一新增类型必须补用途、字段、示例。
3. 禁止 API 层绕过框架层直接写业务逻辑。

