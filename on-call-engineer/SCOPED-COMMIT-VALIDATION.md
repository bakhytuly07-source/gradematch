# Scoped local commit proof (2026-11-14)

The initial live drill exposed a real permission failure: legacy
`--sandbox workspace-write --add-dir MAIN/.git` kept the linked Git index
read-only. The process exited zero without creating a fix commit. This failed
session is retained by QA; it is not a passing fix.

The corrected default adapter uses an explicit named filesystem policy rather
than full access. It permits the assigned worktree and linked Git directory,
common object storage, and oncall reference/log directories. Common index,
main references, shared config, other checkouts and packed references remain
read-only. Agent command network access is disabled; provider authentication
uses Codex's separate client connection. No sandbox bypass is used. Policy
mechanics are documented in the [official permission profiles reference](https://learn.chatgpt.com/docs/permissions).

Engineer executed the real authenticated Codex CLI v0.166.0-alpha.5.1 in a
fresh **disposable** local repository, unrelated to the real fault/oncall
branches. From its linked `oncall/proof` worktree, the agent used a Python
heredoc, changed the fixture `before` to `after`, staged and committed it:

```text
os.access(common/index, os.W_OK) = False
os.access(common/refs/heads/main, os.W_OK) = False
[oncall/proof c1d37a0] test: scoped commit proof
1 file changed, 1 insertion(+), 1 deletion(-)
HEAD=c1d37a0bafc300014b08b5d9196afd81b1264dbc
```

The worktree was clean afterward; main retained its baseline commit. No push,
merge, branch switch, shared config change or escalation occurred. The raw
proof log remains under `/tmp/gradematch-scoped-codex-proof-final.log` for local
inspection. This is a permission proof, **not the GradeMatch fault-drill PASS**.
QA must rerun the full real alert/fix drill separately.

Git reported denial of a common `packed-refs.lock` attempt, then successfully
created the loose oncall reference commit. This protected shared-reference
housekeeping remains denied intentionally. Verify actual new HEAD, ancestry,
branch and diff; neither a zero agent exit nor a log's claim proves a fix.
The launcher now reports unchanged HEAD as `local_fix_commit=none` and
`investigation_result=no_new_commit`; a new descendant on its assigned branch
is reported as `local_commit_created` and still needs QA validation.
