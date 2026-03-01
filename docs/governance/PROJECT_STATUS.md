# 项目状态（交接单一事实源）

## 当前阶段

- 阶段：Protocol 组件已实现并进入审核
- 日期：2026-03-01

## 已完成组件

- [x] Protocol
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

- Engine（loop）（待开始）

## 已通过审核的小步

1. 规则文件中文化与小步约束落地（`docs/governance/NORTH_STAR.md`、`docs/governance/AI_TASK_GUARDRAILS.md`、`AGENTS.md`）
2. 教程目录骨架创建（`docs/tutorials/01..14`）
3. Protocol 组件完成并升级教程质量（`framework/labor_agent/protocol.py`、`tests/test_protocol.py`、`docs/tutorials/09-智能体通信协议.md`）
4. Protocol 代码结构工程化重构（迁移到 `framework/labor_agent/core/protocol/`）并新增系列第一章总览教程
5. 系列第二章 Protocol 教程完成（读者向发布文风，未引入 Engine 实现）

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
12. 已新增教程黄金标准与章节模板，用于锁定跨会话质量一致性。

## 下一步唯一任务

- 后续所有章节先对齐教程黄金标准与模板，再进入对应组件实现。

## 阻塞项

- 无
