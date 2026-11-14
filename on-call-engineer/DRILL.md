# Local fault drill (#135) — QA execution runbook

This file is preparation, **not evidence of a completed drill**. QA executes it
in isolated checkouts after the implementation commits are on main. Never inject
on main, deploy to Render, push either experimental branch, or merge a fix.
The ordinary application and tests retain telemetry off. Dependencies are already
pinned; this drill adds none. Keep the main checkout clean throughout the drill.

## Prerequisites and baseline

Use three terminals, authenticated `codex` CLI (`codex login status`), Python
with the existing backend environment, Git, Docker Compose and the existing
local observability stack. Codex needs network access to its provider and Git
write permission to the common repository metadata to create a local commit.
In a restricted outer sandbox, request the narrow permissions needed for the
poller/agent before starting. Do not replace a real agent with a fixture. If
provider/auth/permissions fail, record BLOCKED and retain the claimed log;
never claim this is a successful investigation.

From the clean main checkout, set absolute paths (retain these across terminals):

```sh
MAIN=$(pwd)
test "$(git branch --show-current)" = main
test -z "$(git status --porcelain)"
BASE_SHA=$(git rev-parse main)
DRILL_BRANCH=inject-bug-$(date -u +%F)
FAULT_TREE=/tmp/gradematch-fault-$(date -u +%Y%m%dT%H%M%SZ)
STATE="$MAIN/on-call-engineer/logs"
PYTHON="$MAIN/backend/.venv/bin/python"
mkdir -p "$STATE"
printf '%s baseline_main=%s\n' "$(date -u +%FT%TZ)" "$BASE_SHA" > "$STATE/drill-evidence.txt"
make obs-up
python3 observability/check.py
codex login status
# These are local only. Never use git push or git merge during the drill.
git worktree add -b "$DRILL_BRANCH" "$FAULT_TREE" "$BASE_SHA"
```

If the dated branch exists, inspect it and choose a fresh execution date or
report the collision; do not reset/delete someone else's evidence. The API
helper defaults to port 8092, environment `drill`, version `fault-drill` to keep
ordinary app traffic out. Ensure no previous alert for this identity is active:

```sh
python3 "$MAIN/on-call-engineer/drill.py" resolve
```

## Fault injection: QA only, in the new checkout

The following guarded edit is executed only in the isolated fault tree. It
inserts an unconditional generation exception inside the existing instrumented
try/except boundary, so valid uploads fail with 500 and increment
`gradematch_generate_failures_total{reason="processing_error"}`. The agent should
identify and remove this actual defect; no production fault switch is added.

```sh
cd "$FAULT_TREE"
test "$(git branch --show-current)" = "$DRILL_BRANCH"
python3 - <<'PY'
from pathlib import Path
import subprocess
branch = subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()
assert branch.startswith('inject-bug-'), 'Never inject on main'
p = Path('backend/app/main.py')
s = p.read_text()
needle = 'async def generate_image(request: Request):\n'
assert s.count(needle) == 1
p.write_text(s.replace(needle, needle + '    raise RuntimeError("Local drill: injected generation defect")\n'))
PY
git add backend/app/main.py
git commit -m 'test: inject local generation failure for observability drill'
INJECT_SHA=$(git rev-parse HEAD)
printf 'inject_branch=%s inject_sha=%s\n' "$DRILL_BRANCH" "$INJECT_SHA" >> "$STATE/drill-evidence.txt"
git log --oneline main..HEAD
git diff main...HEAD -- backend/app/main.py
# Before-fail check uses the real valid upload endpoint below, not invalid input.
cd "$FAULT_TREE/backend"
DATABASE_URL=sqlite:////tmp/gradematch-fault-drill.db "$PYTHON" -m alembic upgrade head
DATABASE_URL=sqlite:////tmp/gradematch-fault-drill.db \
  OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
  DEPLOYMENT_ENVIRONMENT=drill APP_VERSION=fault-drill \
  "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8092
```

Run the app in the foreground; Ctrl-C stops and flushes telemetry before
switching code. Use a disposable database; uploaded originals remain in memory.

## Fire the real alert and run exactly one investigation

In terminal 2, with the same MAIN/STATE/FAULT_TREE variables:

```sh
python3 "$MAIN/on-call-engineer/drill.py" check --expect 500 | tee -a "$STATE/drill-evidence.txt"
python3 "$MAIN/on-call-engineer/drill.py" fire | tee -a "$STATE/drill-evidence.txt"
curl --fail http://localhost:9090/api/v1/alerts > "$STATE/alerts-firing.json"
```

The helper sends one baseline **valid-upload 500**, waits 15s for initial
export/scrape, then sends **one valid-upload 500 every 10s** until firing (300s
bound). #133 requires summed `increase(...[5m]) >= 5` and a full **2m** hold;
continuous traffic maintains that threshold. Export/scrape/evaluation intervals
add delay. All four reasons aggregate, so isolate this identity from other
traffic. The helper prints exact UTC transitions and the matching labels and
`activeAt`, then stops traffic immediately at firing.

Before the rolling window clears, open
[Prometheus alerts](http://localhost:9090/alerts), expand
GradeMatchGenerateFailures and capture a real screenshot showing firing state,
service/environment/version/owner and the visible clock/time. Save under
`docs/img/fault-drill-YYYY-MM-DD-alert.png` in the main checkout for later
sanitized evidence review; screenshot creation is the only planned main
working-tree change during the drill. Do not create a screenshot from fixture
HTML or claim a JSON file is a screenshot.

```sh
python3 "$MAIN/on-call-engineer/poller.py" --repo "$FAULT_TREE" --state "$STATE" \
  --agent "codex exec --sandbox workspace-write --add-dir $MAIN/.git" --dry-run --once
python3 "$MAIN/on-call-engineer/poller.py" --repo "$FAULT_TREE" --state "$STATE" \
  --agent "codex exec --sandbox workspace-write --add-dir $MAIN/.git"
```

Let at least two 60s polls occur for the same firing identity, then Ctrl-C (the
poller waits for active workers). Restart once with `--once` and the same state
to demonstrate durable deduplication. Inspect matching `.claim` and timestamped
`.log`: exactly **one session launch** for that complete label set + activeAt.
Other firing alerts legitimately launch different identities; use a quiet local
stack. If the alert resolves too soon for restart, the durable automated test
still verifies restart behavior; preserve the actual observed poll timestamps.

The log must show `base_branch=inject-bug-...`, `base_commit=INJECT_SHA`, actual
oncall branch/worktree, invocation, investigation output, exit status, and a
**different local_fix_commit SHA**. A successful exit without a fix commit is
not a passing drill. The agent may run the focused existing generation test
using `MAIN/backend/.venv/bin/python -m pytest tests/test_generate.py` from its
own backend directory (no dependency install required). The inherited push hook
and agent instructions prohibit pushes; the launcher never pushes.

## Verify correction, resolve, and prove isolation

Read the log and set `FIX_SHA` and `FIX_TREE` to the actual recorded commit and
worktree; do not guess branch names. Inspect before running fixed code:

```sh
git -C "$MAIN" show "$FIX_SHA"
git -C "$MAIN" diff "$INJECT_SHA...$FIX_SHA" -- backend/app/main.py
test "$FIX_SHA" != "$INJECT_SHA"
# Terminal 1: Ctrl-C the faulty app. Start the fixed app, same identity and port:
cd "$FIX_TREE/backend"
DATABASE_URL=sqlite:////tmp/gradematch-fault-drill.db \
  OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
  DEPLOYMENT_ENVIRONMENT=drill APP_VERSION=fault-drill \
  "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8092
# Terminal 2:
python3 "$MAIN/on-call-engineer/drill.py" check --expect 200 | tee -a "$STATE/drill-evidence.txt"
python3 "$MAIN/on-call-engineer/drill.py" resolve | tee -a "$STATE/drill-evidence.txt"
curl --fail http://localhost:9090/api/v1/alerts > "$STATE/alerts-resolved.json"
test "$(git -C "$MAIN" rev-parse main)" = "$BASE_SHA"
if git -C "$MAIN" merge-base --is-ancestor "$INJECT_SHA" main; then
  echo 'FAIL: main contains injected commit'; exit 1
fi
printf 'main_after=%s fault_not_ancestor=PASS\n' "$(git -C "$MAIN" rev-parse main)" >> "$STATE/drill-evidence.txt"
```

Resolution sends **no failures** and waits up to 360s for the rolling five-minute
window/export/evaluation delay to clear. Record UTC firing, fix start, first 200,
and observed resolution times rather than expected times. If before/after needs
repeating, stop the fixed server, rerun the faulty checkout's server and
`check --expect 500`, stop it, restart the fixed server and `check --expect 200`.
This repeats the same fixture/check and demonstrates cause/correction. It also
adds failure traffic; restart the full resolution wait afterwards.

Stop the drill server/poller. Leave ordinary app telemetry off (unset endpoint;
see observability README). Retain local fault/fix branches and ignored logs for
review. Never push or merge them. Run `git check-ignore` on the full session log.

## Evidence record required for QA PASS

Create a sanitized Markdown record with: baseline and after main SHA; fault
branch/commit and `git log`/`git diff` commands; exact firing alert labels and
activeAt from alerts-firing.json; screenshot relative link; one-session evidence;
redacted short agent output including base/fix branch/SHAs and exit status;
before-500/after-200 outputs; actual resolution/API time and absence of matching
alert; `git show FIX_SHA` instructions; fault-not-ancestor result. Link the local
ignored full log location for local review, but commit only a reviewed excerpt.
Never commit auth material, uploaded bytes, full raw logs, fault code or fix
branch. After the unchanged-main proof, QA may commit **only sanitized evidence**
(screenshot and record); this later evidence commit is separate from the baseline
and does not include the fault or fix. #136 consolidates final documentation.
