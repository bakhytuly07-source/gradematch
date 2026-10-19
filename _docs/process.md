# Process

Tasks are GitHub issues, one at a time. Read the acceptance criteria before starting and before closing. Commit regularly.

## Labels and milestones

- Labels: `mvp`, `post-mvp`, `user-test-bug`
- Milestones, in this order: M1 Frontend + mockService, M2 OpenAPI contract, M3 Backend in-memory, M4 SQLite + ORM, M5 Integration, M6 Tests, docs, polish
- Only `mvp` and `user-test-bug` issues must be closed. `post-mvp` issues stay open

## Roles

- PM - grooms a task before anyone implements it, follows `_docs/team/pm.md`
- Engineer - implements one groomed task, follows `_docs/team/software-engineer.md`
- QA - checks the result against the acceptance criteria, adds test cases, closes the issue on PASS, follows `_docs/team/qa-engineer.md`

## Orchestrator

The main session is the orchestrator. It launches the PM, the engineer and QA as subagents. It does not groom, implement or test itself.

### Lifecycle

1. Pick the next open issue labeled `mvp` or `user-test-bug`: lowest milestone first, `user-test-bug` before `mvp` inside a milestone (`gh issue list --state open --label mvp`)
2. PM grooms it
3. Engineer implements it
4. QA verifies it
5. On FAIL, back to step 3 with the QA comment as input
6. On PASS, QA closes the issue
7. Repeat until no open `mvp` or `user-test-bug` issue is left

### Rules

- Do not skip step 2
- The engineer does not close the issue
- QA does not change production code. QA may add test cases (files under `tests/` or `*.test.ts`) and may add acceptance criteria to the issue
- Only QA closes an issue, and only after PASS
- Each agent starts in a fresh session and gets only the issue and the documents it links

## User-test bugs

When the human finds a bug while running the app:

1. Create an issue with the label `user-test-bug`: Goal (what should be true) and Description (what happened, steps to reproduce)
2. PM grooms it with `_docs/task-template.md`
3. QA adds test cases that fail because of the bug
4. Engineer fixes it
5. QA verifies and closes it on PASS

## Batched mode (deadline)

To fit the deadline the orchestrator may batch: PM grooms all open mvp issues in one session; Engineer implements one milestone per session (one commit per issue); QA verifies one milestone per session but still posts a verdict comment on every issue and closes only the issues that PASS.
