---
name: tutorial-quality-checker
description: 审核与修复教程文章质量。用于检查 docs/tutorials 下章节是否符合固定模板与黄金标准，特别适用于“优化不是重构”场景、命令块渲染错误、文件创建命令缺失、章节结构缺口、代码路径与主线漂移等问题。
---

# Tutorial Quality Checker

执行以下流程审查教程文章，并输出可执行修复建议或直接修复。

## 1. 读取基线文件

优先读取：

1. `docs/tutorials/_CHAPTER_TEMPLATE.md`
2. `docs/tutorials/_TUTORIAL_GOLD_STANDARD.md`
3. 目标章节文件（如 `docs/tutorials/03-*.md`）

## 2. 先做结构体检

检查章节是否包含以下关键段落（允许顺序有轻微调整，但必须齐全）：

1. `目标`
2. `架构位置说明（演进视角）`
3. `前置条件`
4. `本章主线改动范围（强制声明）`
5. `实施步骤`
6. `运行命令`
7. `增量闭环验证`
8. `验证清单`
9. `常见问题`
10. `本章 DoD`
11. `下一章预告`

缺失时：只增量补齐，不重写整章。

## 3. 再做命令块体检

重点检查：

1. 每个“文件：`path`”前是否有创建命令。
2. 创建命令是否同时有 `bash` 和 `powershell` 代码块。
3. 是否存在空代码块（如 ` ```bash` 后直接 ` ````）。
4. 命令是否与实际路径一致（不能伪路径）。

## 4. 做代码漂移体检

将教程中的代码片段与主线真实文件比对，优先检查：

1. 导入路径是否一致（最常见漂移点）。
2. 导出入口（`__init__.py`）是否漏写子包导出。
3. 预期输出是否与真实命令行为一致。

发现漂移时：优先修教程，不随意改主线代码。

其中“代码漂移”是重点检查项，默认必须执行。

## 5. 执行自动检查脚本

运行：

```bash
uv run python skills/tutorial-quality-checker/scripts/check_tutorial_markers.py --file <章节文件路径>
```

```powershell
uv run python skills/tutorial-quality-checker/scripts/check_tutorial_markers.py --file <章节文件路径>
```

说明：

1. 脚本用于快速发现结构/命令块硬伤。
2. 脚本会自动执行代码漂移检查：`文件：[...](path)` 后的代码块需与真实文件一致。
3. 脚本通过不代表质量已达标，仍需人工审阅“叙事清晰度与工程取舍讲解”。

## 6. 输出格式

每次交付使用固定结构：

1. 本步目标
2. 本步改动
3. 验证结果
4. 请审核
