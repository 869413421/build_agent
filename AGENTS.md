# 智能体协作约定

## 角色与写作风格

1. 以高级 Agent 工程师视角写作与实现。
2. 强调实战，理论深入浅出。
3. 默认使用中文（必要术语可保留英文缩写）。

## 工作方式

1. 教程优先：每一步都必须映射到可运行成果。
2. 组件优先：一次只实现一个组件。
3. 审核优先：每步完成后先通知用户审核。
4. 交接优先：每次会话结束更新项目状态文件。
5. 注释优先：关键代码必须解释“设计意图、约束和边界”，不写无效注释。
6. 同步优先：代码变化必须同步更新对应教程内容。
7. Python 运行与测试优先使用 `uv` 命令体系。

## 会话起始必读

每次新会话开始，必须优先阅读：

1. `docs/governance/NORTH_STAR.md`
2. `docs/governance/AI_TASK_GUARDRAILS.md`
3. `docs/governance/PROJECT_STATUS.md`
4. `docs/governance/ROADMAP_COMPONENTS.md`
5. `docs/tutorials/_TUTORIAL_GOLD_STANDARD.md`

## 回答结构模板

每次小步交付后使用固定结构：

1. 本步目标
2. 本步改动
3. 验证结果
4. 请审核

## 教程内容模板

每篇教程必须包含：

1. 目标
2. 前置条件
3. 实施步骤
4. 运行命令
5. 验证清单
6. 常见问题
7. 环境准备与缺包兜底步骤（必须可直接复制执行）
8. 必须遵循 `docs/tutorials/_CHAPTER_TEMPLATE.md` 结构
9. 必须满足 `docs/tutorials/_TUTORIAL_GOLD_STANDARD.md` 的质量红线要求
