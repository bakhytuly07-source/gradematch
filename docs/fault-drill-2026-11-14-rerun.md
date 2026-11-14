# Final fault-drill QA rerun — 2026-11-14

Verdict: **PASS**; this is a new real execution after the sole
permission-adapter fix round. The [initial failed drill](fault-drill-2026-11-14-initial.md)
remains failed evidence. No production code was changed by QA.

## Baseline and local isolation

Source checkout: `/Users/zhaksylykbakhytuly/gradematch`; independent rerun repository:
`/tmp/gradematch-drill-rerun-20261114T080935Z`. Both started from clean main at
`64be0f40f5044b16a5d41299229ec99c69cccbe8` before injection. The clone used `git clone --no-hardlinks
--single-branch --branch main SOURCE CLONE`, preserving the original dated fault
branch, oncall branch, worktrees and claim. A temporary dependency symlink was
removed after agent testing; the directory ignore pattern did not ignore a
symlink. It was never committed and no dependency was installed.

Fault checkout `/tmp/gradematch-fault-rerun-20261114T080935Z`, branch `inject-bug-2026-11-14`,
commit `09c25c848968aae9483260dbe621b561a20db67f`. `git log --oneline main..inject-bug-2026-11-14`
and `git diff main...inject-bug-2026-11-14 -- backend/app/main.py` show exactly
one added unconditional RuntimeError in `generate_image`. No fault switch,
Render deployment, remote fault/fix push or merge occurred.

## Real traffic, firing identity and screenshot

The local API used port 8092, a disposable SQLite database, telemetry endpoint
`http://localhost:4318`, environment `drill`, version `fault-drill`.
A real valid JPEG multipart request returned 500 at 08:10:14.689399Z.
The helper then sent a baseline 500, waited 15s, and sent one valid-upload 500
per 10s until firing. Prometheus evaluates every 5s with a five-minute increase
threshold of 5 and a full two-minute hold.

Pending activeAt: `2026-11-14T08:11:13.695879708Z`.
Firing observed: `2026-11-14T08:13:19.889299Z`; traffic stopped immediately.
The matching `/api/v1/alerts` capture at 08:13:39.325473Z recorded:

```json
{"state":"firing","activeAt":"2026-11-14T08:11:13.695879708Z","labels":{"alertname":"GradeMatchGenerateFailures","environment":"drill","owner":"gradematch-maintainers","service":"gradematch","version":"fault-drill"}}
```

[Actual Prometheus screenshot](img/fault-drill-2026-11-14-rerun-alert.png),
captured 08:14:43.921Z from the real local UI. It shows FIRING, all five labels
and the exact Active Since timestamp tooltip matching the API. No fixture HTML
or screenshot modification was used.

## Exactly one real investigation and local fix

A real dry run at 08:13:39Z printed identity, planned branch and default adapter
without creating a claim/session/branch. Continuous polling started 08:13:48Z,
ran through 08:16:06Z (immediate poll plus two 60s repeat polls), then stopped.
Restart `--once` at 08:16:09Z while the API still showed this same firing
identity retained exactly one claim and one timestamped session log.
The automated fake-clock, slow-worker and durable restart tests also pass.

Reviewed excerpt from the ignored real session:

```text
08:13:48.299350Z base_branch=inject-bug-2026-11-14 base_commit=09c25c848968aae9483260dbe621b561a20db67f
08:13:48.380973Z branch=oncall/GradeMatchGenerateFailures-20261114T081348Z
command=python3.14 CLONE/on-call-engineer/codex_agent.py -
08:14:33.098234Z focused valid-image test: 1 failed (500 rather than 200)
08:14:49.498954Z same focused test after correction: 1 passed
08:14:56Z relevant generation/API/extraction/metrics tests: 40 passed
08:14:57.537055Z [oncall/GradeMatchGenerateFailures-20261114T081348Z 3ed5e23] fix: restore image generation by removing injected exception
08:15:07.152210Z exit_status=0 investigation_result=local_commit_created
local_fix_commit=3ed5e23fbe22c0bbd2bf5ae0d5c6df6f414d37a8
```

The named scoped policy permits the assigned worktree/linked metadata, objects,
and oncall refs. Git denied shared `packed-refs.lock` housekeeping, but actually
created the loose oncall reference commit. QA independently verified the new
HEAD, descendant ancestry, assigned branch, clean worktree and one-line diff:
only the injected RuntimeError is removed. The agent's initial offline uv
attempt found no cached dependencies; it reused the installed environment and
installed none. No sandbox bypass or credential output was needed.

Local review (these commits exist only in the independent local repository):

```sh
git -C /tmp/gradematch-drill-rerun-20261114T080935Z show 3ed5e23fbe22c0bbd2bf5ae0d5c6df6f414d37a8
git -C /tmp/gradematch-drill-rerun-20261114T080935Z diff 09c25c848968aae9483260dbe621b561a20db67f...3ed5e23fbe22c0bbd2bf5ae0d5c6df6f414d37a8 -- backend/app/main.py
```

Full raw log remains ignored, not published:
`/tmp/gradematch-drill-rerun-20261114T080935Z/on-call-engineer/logs/20261114T081348Z-1c853f1502e59533b550b572460998e29f111fe585006b85850f11a996b0b7ce.log`.
`git -C CLONE check-ignore FULL_LOG` exits 0. The single `.claim` filename is
`1c853f1502e59533b550b572460998e29f111fe585006b85850f11a996b0b7ce.claim`.

## Live correction, resolution and unchanged main

QA stopped the faulty server, inspected the committed correction, then started
the fixed checkout with the same database, telemetry identity and port.
Fixed server start `2026-11-14T08:15:26.851324+00:00`; the same valid-upload helper returned 200 at
`2026-11-14T08:15:37.767598Z`. Resolution sends no failures.

Actual resolution observed `2026-11-14T08:17:47.926747Z`: no matching alert
remained in `/api/v1/alerts`, 268s after firing traffic stopped. Independent
final API capture at `2026-11-14T08:18:19.190672+00:00` also contained an empty alerts array.
Both drill API and poller were stopped after verification. Final unchanged-main
proof before evidence publication again passed for source and clone; fault
ancestry in clone exited 1.

At `2026-11-14T08:16:21.858605+00:00`, both source and clone main still equalled
`64be0f40f5044b16a5d41299229ec99c69cccbe8`. Clone `git merge-base --is-ancestor INJECT_SHA main`
exited 1. Source `git cat-file -e INJECT_SHA^{commit}` failed because the
independent fault object never entered source. Source main remained clean;
clone main had only the planned screenshot after temporary symlink removal.
Clone remote refs contain only origin/main at the baseline, no experimental
branches. No fault/fix push, merge, shared config edit or deployment occurred.
The ordinary Docker app retains telemetry off.

## Independent final-code checks

- `cd backend && uv run pytest`: 222 passed, 1 optional PostgreSQL skip.
- `python3 -m unittest discover -s on-call-engineer/tests -v`: 26 passed.
- `OTEL_EXPORTER_OTLP_ENDPOINT= make integration`: 10 passed.
- `cd frontend && npm test -- --run`: 52 passed.
- `OTEL_EXPORTER_OTLP_ENDPOINT= make e2e`: 30 Playwright tests plus guest,
  library and account-switch runner scenarios passed. Existing preview timing
  diagnostics 365–433ms exceed 300ms target without assertion failures; unchanged
  from the prior checks and unrelated to this adapter correction.

No dependencies, contract, telemetry defaults or Render configuration changed.
After the final unchanged-main proof, only this sanitized record and reviewed
screenshot may be copied to source and committed as separate QA evidence.
