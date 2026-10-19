#!/usr/bin/env bash
# Run from any directory. Requires Python 3 and an authenticated gh CLI.
# Optional first argument: OWNER/REPO; otherwise use this checkout's repository.
# Existing labels, milestones and exact issue titles (open or closed) are skipped.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
exec python3 - "$project_root/_docs/tasks.md" "${1:-}" <<'PY'
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

milestones = {
    'M1': 'M1 Frontend + mockService',
    'M2': 'M2 OpenAPI contract',
    'M3': 'M3 Backend in-memory',
    'M4': 'M4 SQLite + ORM',
    'M5': 'M5 Integration',
    'M6': 'M6 Tests, docs, polish',
}

def gh(*args, already_exists=False):
    result = subprocess.run(['gh', *args], text=True, capture_output=True)
    if result.returncode:
        message = result.stderr + result.stdout
        # Ignore only duplicate-resource failures, not auth/network/permission errors.
        if already_exists and re.search(r'already exists', message, re.I):
            return None
        raise SystemExit(f"gh {args[0]} failed: {message.strip()}")
    return result.stdout

# Validate the entire backlog before performing any remote mutations.
source = Path(sys.argv[1]).read_text()
pattern = re.compile(
    r'## (\d+)\. ([^\n]+)\nMilestone: (M[1-6])\n'
    r'Label: (mvp|post-mvp)\nGoal: ([^\n]+)\nDescription: ([^\n]+)'
)
blocks = source.strip().split('\n\n')
tasks = []
for expected, block in enumerate(blocks, 1):
    match = pattern.fullmatch(block)
    if not match or int(match[1]) != expected:
        raise SystemExit(f'Invalid task format or numbering at task {expected}')
    number, title, milestone, label, goal, description = match.groups()
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', description)
    if not 2 <= len(sentences) <= 3:
        raise SystemExit(f'Task {number} needs two or three description sentences')
    tasks.append((f'{number}. {title}', milestone, label, goal, description))
counts = collections.Counter(m for _, m, label, _, _ in tasks if label == 'mvp')
if len(tasks) != 86 or counts != dict(zip(milestones, [12, 4, 20, 12, 10, 8])):
    raise SystemExit('Expected 86 tasks and MVP milestone counts 12/4/20/12/10/8')
if sum(label == 'post-mvp' for _, _, label, _, _ in tasks) != 20:
    raise SystemExit('Expected 20 post-mvp tasks')
repo = sys.argv[2] or json.loads(gh('repo', 'view', '--json', 'nameWithOwner'))['nameWithOwner']
if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
    raise SystemExit('Repository must be OWNER/REPO')
for label, color in [('mvp', '0E8A16'), ('post-mvp', '5319E7'), ('user-test-bug', 'D73A4A')]:
    gh('label', 'create', label, '--repo', repo, '--color', color, already_exists=True)

def pages(endpoint):
    return json.loads(gh('api', '--paginate', '--slurp', endpoint))

existing_milestones = {
    item['title'] for page in pages(f'repos/{repo}/milestones?state=all&per_page=100') for item in page
}
for name in milestones.values():
    if name not in existing_milestones:
        gh('api', '--method', 'POST', f'repos/{repo}/milestones', '-f', f'title={name}', already_exists=True)
# Include closed issues and paginate so rerunning after partial completion is safe.
existing_titles = {
    item['title'] for page in pages(f'repos/{repo}/issues?state=all&per_page=100')
    for item in page if 'pull_request' not in item
}
for title, milestone, label, goal, description in tasks:
    if title in existing_titles:
        print(f'Skipping existing issue: {title}', flush=True)
        continue
    body = f'Goal: {goal}\n\nDescription: {description}\n'
    url = gh('issue', 'create', '--repo', repo, '--title', title,
             '--label', label, '--milestone', milestones[milestone], '--body', body,
             already_exists=True)
    if url:
        print(url.strip(), flush=True)
    existing_titles.add(title)
PY
