# 项目状态（交接单一事实源）

## 当前阶段

- 阶段：规则治理完成，准备回到组件级小步实施
- 日期：2026-03-01

## 已完成组件

- [ ] Protocol
- [ ] Engine（loop）
- [ ] Model Runtime（LLM Adapter）
- [ ] Tool Runtime（API Adapter）
- [ ] Observability
- [ ] Context Engineering
- [ ] Retrieval
- [ ] Memory
- [ ] Evaluator
- [ ] Safety Layer

## 进行中组件（唯一）

- Protocol（待开始）

## 已通过审核的小步

1. 规则文件中文化与小步约束落地（`NORTH_STAR.md`、`AI_TASK_GUARDRAILS.md`、`AGENTS.md`）
2. 教程目录骨架创建（`docs/tutorials/01..14`）

## 技术债与偏差

1. 当前代码目录已存在多组件一次性实现痕迹，不符合“单组件小步”节奏。
2. 下一步需以 Protocol 为起点，逐步清理并重构流程。
3. 组件顺序已固定为 10 项，不再新增组件条目；缺失能力通过 DoD 约束内化到现有组件。

## 下一步唯一任务

- 仅实现和整理 Protocol 组件（类型、校验、最小测试、对应教程），不触及其他组件逻辑扩展。

## 阻塞项

- 无
