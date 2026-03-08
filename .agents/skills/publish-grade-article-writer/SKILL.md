---
name: publish-grade-article-writer
description: Write or heavily rewrite publish-grade technical tutorials, architecture chapters, and code-explainer articles from scratch. Use when Codex needs to produce high-quality long-form technical writing that must stay aligned with real code, include runnable commands/tests/examples, explain architecture and tradeoffs clearly, and satisfy repository writing standards such as docs/tutorials chapters, project guides, or engineering deep dives.
---

# Publish Grade Article Writer

Write technical articles that are code-aligned, readable, and publication-grade. Default to direct execution: outline, write, validate, and update project status instead of only giving advice.

## Core workflow

### 1. Load the writing baseline first

When the target is inside `docs/tutorials/` or the repository has explicit writing standards, read them before writing.

In this repository, prefer this order:

1. `docs/tutorials/_TUTORIAL_GOLD_STANDARD.md`
2. `docs/tutorials/_CHAPTER_TEMPLATE.md`
3. `docs/governance/NORTH_STAR.md`
4. `docs/governance/AI_TASK_GUARDRAILS.md`
5. `docs/governance/PROJECT_STATUS.md`
6. `docs/governance/ROADMAP_COMPONENTS.md`

If the article explains existing code, also read the exact source files and tests that the article will cover.

For the repo-specific quality bar and validation checklist, read:

1. [references/repo-article-standard.md](references/repo-article-standard.md)
2. [references/article-checklist.md](references/article-checklist.md)

### 2. Decide the article mode before writing

Use one of these modes:

1. **New chapter**: a new tutorial/chapter built around already-implemented code.
2. **Heavy rewrite**: an existing article is structurally weak and needs a new main narrative.
3. **Precision enhancement**: the article is mostly correct, but needs terminology, reader handrails, examples, or stronger code explanations.

Do not mix modes blindly. If the request is “rewrite from scratch”, treat it as a heavy rewrite. If the request is “polish” or “scan once”, treat it as precision enhancement.

### 3. Lock the article spine before editing

Before writing body text, make sure the article can answer these questions clearly:

1. What exact system capability does this article add or explain?
2. Where does that capability sit in the architecture?
3. Why must it be introduced now rather than earlier or later?
4. What files, tests, and examples make the capability real?

For tutorial chapters, the narrative order must stay:

1. Goal / capability
2. Architecture position
3. Prerequisites
4. Main flow first (“面”)
5. Implementation details (“点”)
6. Commands and validation
7. FAQ / failure modes
8. DoD / next chapter

### 4. Write for first-read comprehension, not only correctness

Always add reader handrails when the topic is dense.

Preferred patterns:

1. `## 如果你第一次接触 ...` to compress the chapter into 3-4 key ideas.
2. `## 名词速览` to flatten terminology before code.
3. `第一次读 ...` or `先抓这 ...` sections for large files or deep chapters.
4. Life-like or engineering examples when a concept is abstract.

Use these handrails especially for runtime, engine, retrieval, observability, or architecture-heavy chapters.

### 5. Make code explanations deep enough

For every major code block or major source file:

1. Explain the design motivation.
2. Explain where it sits in the architecture.
3. Explain engineering tradeoffs.
4. Explain failure modes / boundary conditions.
5. Give at least one success-path example.
6. Give at least one failure-path example.
7. Add a Mermaid flowchart or sequence diagram if the logic is multi-step.

Simple export files like `__init__.py` can be explained briefly. Core runtime or orchestration files must be explained deeply.

### 6. Keep articles aligned with real files

Never write tutorial code that drifts from the repository unless the task explicitly includes code changes.

If editing an existing article with code blocks:

1. Snapshot code blocks first with the local guard script if available.
2. Update the article against the current source of truth.
3. Re-run the guard after editing.

If the article is about a file that is too large to print in full, use an explicit excerpt and state that it is an excerpt. Also point to the real file path.

### 7. Validate before finishing

If the repository provides article validation scripts, use them.

In this repository, prefer:

1. `python .agents/skills/tutorial-quality-checker/scripts/check_tutorial_markers.py --file <article>`
2. `python .agents/skills/publish-grade-article-auditor/scripts/code_block_guard.py inventory --file <article> --out <snapshot>` before editing existing tutorials
3. `python .agents/skills/publish-grade-article-auditor/scripts/code_block_guard.py verify --before <snapshot> --file <article>` after editing existing tutorials
4. `python .agents/skills/publish-grade-article-writer/scripts/run_article_checks.py --file <article> [--snapshot <snapshot>]`

If the article explains code behavior, run the relevant tests when feasible.

If you want one command for the common tutorial validation chain in this repository, use the bundled script:

`python .agents/skills/publish-grade-article-writer/scripts/run_article_checks.py --file <article> --snapshot <snapshot>`

### 8. Close the loop

When working in this repository, update:

1. `docs/governance/PROJECT_STATUS.md`
2. `docs/governance/HANDOFF_CHECKLIST.md`

Keep the note factual: what article changed, what validation passed, and whether code changed.

## Non-negotiable rules

1. Do not write generic theory-first filler.
2. Do not write “完整见仓库” instead of giving the required code.
3. Do not invent files, commands, outputs, or paths.
4. Do not collapse architecture, implementation, and validation into one section.
5. Do not treat examples and tests as optional appendices if they are part of the teaching value.
6. Do not delete existing code blocks when enhancing an existing article.
7. Do not break the repository's established command-fence convention. If the repo uses ` ```codex `, keep using it consistently.

## Output expectation

The finished article should let a strong but non-expert reader answer:

1. What problem this chapter/article solves.
2. Why the implementation is structured this way.
3. How the main code path runs.
4. How to run and verify it.
5. What breaks when a boundary is violated.
