# 组件实施路线图（强制顺序，10 项不扩项）

## 顺序总览

1. Protocol
2. Engine（loop）
3. Model Runtime（LLM Adapter）
4. Tool Runtime（API Adapter）
5. Observability
6. Context Engineering
7. Retrieval
8. Memory
9. Evaluator
10. Safety Layer

## 生产加严基线（适用于全部 10 组件）

1. 全链路版本治理：`protocol_version`、`config_version`、`model_version`、`tool_version`、`retriever_version`、`evaluator_version`、`policy_version` 必须可追踪。
2. 并发与隔离：运行态按 `tenant_id/user_id/session_id/run_id` 隔离，禁止串写。
3. 回放一致性：replay 必须复现步骤结构与策略分支，不要求字面输出完全一致。
4. 故障域控制：超时、重试、熔断、限流都必须可配置且可观测。
5. 隐私与脱敏：日志/trace/审计默认脱敏，可配置可审计。
6. 评测门禁：离线回归与在线指标阈值必须可阻断发布。

---

## 1) Protocol

### 产出

1. `AgentMessage`、`AgentState`、`ToolCall`、`ToolResult`、`ExecutionEvent`、`FinalAnswer` schema
2. `protocol_version` 字段（所有运行记录强制携带）
3. 统一错误 schema（`error_code`、`error_message`、`retryable`）

### 强制验收（DoD）

1. 所有 schema 有字段级校验与示例
2. tool call 输入/输出都可序列化
3. 协议版本可在 trace 中查询
4. 协议演进需定义兼容策略（新增字段默认兼容，破坏性改动必须升版本）
5. 提供兼容性自动测试：旧记录可被新版本 parser 读取或迁移
6. 预留扩展字段区（如 `extensions`），避免频繁破坏性升版

---

## 2) Engine（loop）

### 产出

1. 标准执行循环：`plan -> act -> observe -> reflect -> update -> finish`
2. 运行时 state store（最小 in-memory，支持 JSON 序列化）
3. 中断与恢复能力：`max_steps`、`time_budget_ms`、`snapshot/restore`
4. 反思策略接口（`ReflectPolicy`）与触发条件（失败触发/低置信触发）

### 强制验收（DoD）

1. 超步数与超时都能优雅结束并返回原因
2. 可在固定配置下跑“确定性回归模式”
3. state 可导出完整执行轨迹
4. 反思事件必须写入 trace，且可被评测系统读取
5. 提供最小性能基线（至少包含 steps/s、P95 latency、error rate）
6. 并发压测下无 state 串写、无 trace 错位、无 step 冲突
7. restore 后不会重复推进副作用步骤（需与 tool 幂等联动）

---

## 3) Model Runtime（LLM Adapter）

### 产出

1. 统一模型调用接口与 provider 映射
2. 结构化输出校验与有限次自修复重试
3. 统一错误分类接入（Timeout、RateLimit、BadSchema 等）
4. token/latency/cost（最小可为空 cost）统计

### 强制验收（DoD）

1. 同一协议输入可切换至少 2 种 provider stub/实现
2. schema 失败触发修复重试并可追踪
3. 统计数据写入 trace
4. 运行时必须通过抽象接口注入，禁止在 Engine 内硬编码 provider
5. 模型降级与切换决策可配置、可追踪、可回放
6. 结构化修复重试有上限且记录修复策略版本

---

## 4) Tool Runtime（API Adapter）

### 产出

1. 工具注册、参数校验、超时/重试
2. 幂等机制（`tool_call_id` 去重）
3. 最小权限模型（`principal` + `capabilities`）
4. Safety-Tool 前置能力：工具白名单、参数范围校验

### 强制验收（DoD）

1. 工具异常统一转换为 error code
2. 重试不重复执行副作用工具
3. 每次工具执行都有可回放记录
4. 工具通过注册机制扩展，新增工具不需要修改 Engine 核心代码
5. 连续失败触发熔断并记录事件，恢复策略可配置
6. 敏感参数默认脱敏，不得明文落 trace/log

---

## 5) Observability

### 产出

1. trace 字段最小集：`trace_id/run_id/step_id/parent_step_id/model_id/tool_name/start_ts/end_ts/error_code`
2. 结构化日志与关键指标（成功率、失败率、耗时）
3. replay 最小实现（基于录制的 tool result）

### 强制验收（DoD）

1. 给定 trace + tool 录制结果可重放步骤结构
2. 任意失败可定位到 step 级原因
3. 采样策略可配置（错误全量、成功抽样）
4. 指标与日志可通过 `run_id/trace_id` 双向关联

---

## 6) Context Engineering

### 产出

1. `ContextBundle` 标准产物（system/messages/tools/citations/budget_report）
2. token 预算裁剪与优先级规则
3. 注入规则：system/developer/tool instruction 的固定合并策略

### 强制验收（DoD）

1. 超预算可稳定降级
2. 被裁剪内容有审计记录
3. 关键指令不被低优先级内容覆盖
4. ContextBundle 生成结果具备黄金样例回归（输入输出 diff 可审计）
5. 模板与提示词必须版本化并写入 trace

---

## 7) Retrieval

### 产出

1. 抽象接口：`Retriever`、`Document`、`Citation`
2. 检索 + 重排 + 引用标准化
3. 最小回归集（10~20 条）

### 强制验收（DoD）

1. 输出可追溯到 citation
2. 检索失败有降级策略
3. 回归集可自动跑通
4. trace 中记录 index/reranker/filter 版本与参数
5. 回放模式可固定检索候选，保障评测可重复

---

## 8) Memory

### 产出

1. 区分 session memory 与 long-term memory
2. 写入触发策略（finish/关键事实/用户偏好）
3. 压缩与冲突策略（最小：last-write-wins + 来源记录）

### 强制验收（DoD）

1. 写入策略可测试
2. 读取结果可解释（来源、时间、范围）
3. 过期与窗口策略生效
4. 记忆读写必须带租户/用户隔离键并可审计
5. 支持删除与失效（纠错/撤回）流程

---

## 9) Evaluator

### 产出

1. 离线评测 + 在线指标聚合
2. 指标三类最小集：
   - 可靠性：成功率、工具失败率、重试率、schema 失败率
   - 效率：steps、token、latency、cost
   - 质量：任务完成度（规则或 judge，需版本化）
3. 从 trace/state 取数，不另起埋点体系

### 强制验收（DoD）

1. 指标计算可复现
2. 回归门槛可配置且生效（如成功率不降）
3. 评测数据集、评分器与规则必须版本化
4. 指标门禁可直接阻断发布流程

---

## 10) Safety Layer

### 产出

1. Safety-Policy：免责声明、越界拦截、转人工规则
2. policy 配置化（YAML/JSON/配置对象）
3. 审计记录：触发规则、证据片段、处理动作

### 强制验收（DoD）

1. 高风险请求必有可追踪拦截记录
2. 所有法律输出自动带免责声明
3. 安全策略变更可版本化追踪
4. 风险分级与动作矩阵（允许/拒绝/降级/转人工）必须配置化
5. 审计证据片段默认脱敏且最小化留存

