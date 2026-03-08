# Article Checklist

Use this checklist before and after writing a technical tutorial or architecture article.

## Before writing

1. Confirm the exact code scope: source files, tests, examples, and any docs the article must align with.
2. Decide the article mode: new chapter, heavy rewrite, or precision enhancement.
3. Lock the article spine: capability, architecture position, why now, and validation path.
4. If editing an existing tutorial with code blocks, create a `code_block_guard` snapshot first.

## While writing

1. Keep the narrative order stable: goal -> architecture -> prerequisites -> main flow -> implementation -> commands -> validation -> FAQ -> DoD -> next step.
2. Add reader handrails if the topic is dense:
   - `如果你第一次接触 ...`
   - `名词速览`
   - `第一次读 ...` / `先抓这 ...`
3. Make every major code explanation answer:
   - what problem this file solves
   - where it sits in the architecture
   - what tradeoff it makes
   - what failure mode it must contain
4. Keep commands runnable and paths real.
5. Treat tests and examples as first-class teaching material, not appendices.

## Before finishing

1. Run the structure checker.
2. Re-run `code_block_guard verify` if the article existed before.
3. Run relevant tests if the article explains behavior that changed.
4. Check that Mermaid diagrams still render in a simple, stable syntax.
5. Update project status / handoff notes if the repository workflow requires it.

## Final quality questions

A publish-grade article should let the reader answer:

1. What exact problem is being solved?
2. Why is the implementation structured this way?
3. How does the main code path run?
4. How do I run and verify it?
5. What breaks if a boundary is violated?
