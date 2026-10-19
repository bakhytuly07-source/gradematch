# GradeMatch documentation

Start with the [local setup and tests](../README.md).

| Review artifact | Location | What to verify |
| --- | --- | --- |
| #13 API contract audit | [13-operation table](./contract-audit.md#operation-audit-table) | Every service method, operationId, route/method, request/response, statuses and security |
| #66 Release evidence | [Release checklist](./release-checks.md) | Reproducible setup/tests, recorded results and pending qualification |
| Product requirements | [MVP scope](./plan.md) | Upload behavior, controls, exports, privacy and extraction limits |
| Working process | [Process](./process.md) | Engineer implementation and QA verification/closure responsibilities |

Current [test execution and setup results](./release-checks.md#current-verification-run)
include the [raw guest browser record](./release-evidence-2026-10-20.json),
explicit Library startup/upload failure, and pending release checks.

The audit table and release checklist are committed documentation artifacts.
Passing unit tests alone does not resolve the extraction quality NO-GO in
[the retained color experiment](../backend/evaluation/README.md).
