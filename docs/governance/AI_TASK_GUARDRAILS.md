# AI 任务执行规则

## 强制对齐

执行任何任务前，必须先阅读：

1. `docs/governance/NORTH_STAR.md`
2. `docs/governance/AI_TASK_GUARDRAILS.md`
3. `AGENTS.md`
4. `docs/governance/PROJECT_STATUS.md`
5. `docs/tutorials/_TUTORIAL_GOLD_STANDARD.md`

## 硬约束

1. 所有协作沟通与教程默认使用中文。
2. 全仓文件统一为 UTF-8（无 BOM），禁止混用本地编码。
3. 框架层设计必须保持领域无关，不绑定单一业务场景字段。
4. 业务场景约束（如法律免责声明）只能出现在应用层，不应固化在通用协议层。
5. 每次只实现一个框架组件，不允许跨组件大步提交。
6. 每步必须同时提交：代码 + 测试 + 教程。
7. 代码必须包含清晰、明确的关键注释，解释意图与边界条件。
8. 未经用户审核“通过”，禁止进入下一步。
9. 注释风格必须强调“为什么这样设计”，不能只描述代码表面行为。
10. 任何代码结构或注释风格变化，必须同步更新对应教程章节。
11. 执行 Python 相关命令时优先使用 `uv`（如 `uv run ...`、`uv sync --dev`）。
12. 新增或修改教程时，必须以 `docs/tutorials/_CHAPTER_TEMPLATE.md` 为骨架，并满足黄金标准。

## 质量门禁

1. 功能变更必须同步更新测试。
2. API/Schema 与实现必须保持一致。
3. 设计变化必须记录到 `docs/architecture/`。
4. 会话结束前必须更新 `docs/governance/PROJECT_STATUS.md` 与 `docs/governance/HANDOFF_CHECKLIST.md`。

## 完成定义（DoD）

1. 本地可运行。
2. 对应测试通过。
3. 对应教程可复现。
4. 安全边界未被破坏。
