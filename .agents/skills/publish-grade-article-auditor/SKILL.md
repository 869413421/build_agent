---
name: publish-grade-article-auditor
description: 出版级技术文章深度审核与优化技能。用于审核并优化 docs/tutorials 及用户自定义 Markdown 技术文章：重排版提升可读性、加强每段主要代码的深度讲解（主流程拆解+成功/失败案例+图示+工程取舍），并严格保证不删减任何原有代码块。适用于“文章质量升级、结构重排、讲解加深、保持代码不丢失”的场景。
---

# Publish Grade Article Auditor

按以下流程执行“审核 + 优化”，默认主动完成编辑，不只给建议。

## 1. 读取基线

必读：

1. `docs/tutorials/_TUTORIAL_GOLD_STANDARD.md`
2. `docs/tutorials/_CHAPTER_TEMPLATE.md`
3. `docs/governance/AI_TASK_GUARDRAILS.md`
4. 目标文章

如果目标不在 `docs/tutorials/`，仍按同一质量标准执行。

## 2. 先做“代码零删减”基线快照（强制）

优化前先执行：

```bash
uv run python skills/publish-grade-article-auditor/scripts/code_block_guard.py inventory --file <文章路径> --out .tmp/code-inventory.json
```

```powershell
uv run python skills/publish-grade-article-auditor/scripts/code_block_guard.py inventory --file <文章路径> --out .tmp/code-inventory.json
```

说明：

1. 该快照用于保证“优化过程不删减任何原有代码块”。
2. 允许新增讲解、图示、示例代码；不允许减少已有代码块内容。
3. 若 `uv` 因本机缓存权限失败，可直接用 `python skills/publish-grade-article-auditor/scripts/code_block_guard.py ...` 作为兜底。

## 3. 审核维度（出版级）

按下列维度逐条审查，并直接修复：

1. 排版组织：标题层次、段落长度、过渡语、读者路径是否顺畅。
2. 主线连续性：是否“先面后点”，是否存在读到文末才补关键认知的断层。
3. 代码讲解深度：
   - 每段主要代码必须有主流程拆解。
   - 每段主要代码必须有成功例子和失败例子。
   - 多步骤机制必须配流程图或时序图。
   - 必须解释工程取舍与边界条件。
4. 工程可执行性：命令、路径、输出预期、常见错误排查是否闭环。
5. 风格一致性：禁止补丁式口吻，新增内容必须自然融合正文。

## 4. 主动优化策略（不是只提建议）

当发现问题时，默认直接改文档：

1. 结构重排：把关键认知从文末前移到进入实现前。
2. 讲解补强：在主要代码段后补“主流程拆解 + 成功/失败案例 + 图示 + 取舍/边界”。
3. 阅读减阻：补清晰过渡句、统一术语、拆分超长段。
4. 保真约束：不删减原有代码块。

## 5. 优化后强制校验（代码零删减）

优化后执行：

```bash
uv run python skills/publish-grade-article-auditor/scripts/code_block_guard.py verify --before .tmp/code-inventory.json --file <文章路径>
```

```powershell
uv run python skills/publish-grade-article-auditor/scripts/code_block_guard.py verify --before .tmp/code-inventory.json --file <文章路径>
```

若校验失败：

1. 立即回查丢失/变更的代码块。
2. 修复后再次验证，直到通过。
3. 若 `uv` 无法执行，使用 `python` 直跑同命令完成校验。

## 6. 输出格式

每次交付统一输出：

1. 本步目标
2. 本步改动
3. 验证结果（含代码零删减校验结果）
4. 请审核

## 7. 约束

1. 除用户明确要求，不得简化或删除任何原有代码块。
2. 若文章存在多个主要代码文件，必须逐个补齐深度讲解，不能只补一个。
3. 优化以“可读性+工程准确性”为目标，不做华而不实文案润色。
