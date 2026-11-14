# Local on-call investigator

Requires Python 3.12, Git, and an installed/authenticated `codex` CLI (`codex login`
then `codex exec --help`). No new Python packages. Start the local Prometheus
stack using [the observability runbook](../observability/README.md).

From the repository root:

```sh
python3 -m unittest discover -s on-call-engineer/tests -v
python3 on-call-engineer/poller.py --dry-run --once
python3 on-call-engineer/poller.py
# Ctrl-C stops polling, then waits for active investigations.
```

Polls immediately and every 60 seconds; API requests time out after 10s. Only
firing alerts launch a worker. Workers run concurrently with polling. State and
session logs live in ignored `on-call-engineer/logs/`. Keep this directory across
restarts: a SHA256 filename claim records the sorted complete label set and
activeAt **before** any launch. Failures remain claimed to avoid retry storms.
Changed labels or start time launch a new investigation. To retry manually,
review the failed log before deleting that specific `.claim`; never delete the
whole directory while workers run. `--state` can select an absolute shared state
directory; use the same directory across restarts/worktree checkouts.

Dry run prints identity, planned UTC branch and invocation, without creating
state, processes or branches. Actual branch names are `oncall/<sanitized-alert>-<UTC>`;
existing names receive a numeric suffix. The committed HEAD of `--repo` is the
base; dirty files in the source checkout remain untouched and are not copied.
Each worker uses its own Git worktree. Do not start multiple distinct state
directories for the same source. Session logs include base branch/commit,
identity, actual branch/command, streamed output, exit code and resulting HEAD.
Common bearer tokens, URL credentials and named secrets are redacted; review
logs manually before publishing any excerpt. Raw logs are never evidence to commit.

The launcher never invokes push; the agent is explicitly forbidden from pushing
and inherits a rejecting pre-push hook. These are local safeguards, not a security
boundary against a malicious agent overriding Git settings. Review all fixes:

```sh
git branch --list 'oncall/*'
git show LOCAL_FIX_SHA
git diff BASE_SHA...LOCAL_FIX_SHA
# Inspect/test in the logged worktree; do not push or merge automatically.
git check-ignore on-call-engineer/logs/example.log
```

The default agent is the bundled `codex_agent.py` adapter using a named scoped
permission profile (Codex CLI with permission-profile support required). It
ignores user config to avoid legacy sandbox overrides; existing authentication
and managed restrictions still apply. It writes only its worktree, assigned
Git metadata, common objects and oncall refs/logs. Main metadata stays read-only;
command network is disabled. No full-access mode is used. See the
[official permissions documentation](https://learn.chatgpt.com/docs/permissions)
for named profiles and precedence. `--add-dir MAIN/.git` with legacy
workspace-write does not grant the linked Git metadata access needed to commit.

`--agent` remains configurable for another installed headless CLI or a test
fixture accepting prompt stdin (`-` appended). Replacing the default adapter also
replaces its permission policy; review that policy before use. An unchanged HEAD
is recorded as `investigation_result=no_new_commit local_fix_commit=none`, even
when the agent exits zero. A new descendant commit on its assigned branch is
recorded as `local_commit_created`; review its diff and tests before accepting it.
`--once` polls once and waits for workers. API/JSON/launch/agent failures are
logged and do not stop future polls. Claims survive a crash, including a crash
between claiming and launching; operator review is required in that case.
