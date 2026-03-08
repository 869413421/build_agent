# Repo Article Standard

Use this reference when the skill is writing inside `docs/tutorials/` for this repository.

## 1. Hard structure for tutorial chapters

A chapter should normally contain these sections:

1. `目标`
2. `架构位置说明`
3. `前置条件`
4. `本章主线改动范围`
5. `实施步骤`
6. `运行命令`
7. `增量闭环验证`
8. `验证清单`
9. `常见问题`
10. `本章 DoD`
11. `下一章预告`

## 2. Chapter writing order

Always write “面” before “点”:

1. Explain the main flow and architecture position first.
2. Then go into files, classes, tests, and examples.

If the chapter is hard to parse on first read, add:

1. `如果你第一次接触 ...`
2. `名词速览`
3. `第一次读 ...` / `先抓这 ...`

## 3. Code explanation depth

For every major code file:

1. Explain the main flow.
2. Explain success path.
3. Explain failure path.
4. Explain tradeoffs and boundaries.
5. Add a Mermaid diagram if the logic is multi-step.

## 4. Existing article enhancement workflow

When editing an existing tutorial:

1. Run `code_block_guard.py inventory` before edits.
2. Edit the article.
3. Run `code_block_guard.py verify` after edits.
4. Run `check_tutorial_markers.py` after edits.

## 5. Repo-specific closure steps

After substantial article work in this repository, update:

1. `docs/governance/PROJECT_STATUS.md`
2. `docs/governance/HANDOFF_CHECKLIST.md`

## 6. What good looks like

A finished chapter should be:

1. runnable
2. code-aligned
3. architecture-driven
4. easy to enter on first read
5. explicit about commands, tests, and failure modes
