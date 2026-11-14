"""Run Codex with narrowly scoped local oncall commit permissions."""
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def command():
    worktree = Path(git('rev-parse', '--show-toplevel')).resolve()
    gitdir = Path(git('rev-parse', '--absolute-git-dir')).resolve()
    common = Path(git('rev-parse', '--git-common-dir')).resolve()
    branch = git('branch', '--show-current')
    if not branch.startswith('oncall/') or gitdir == common:
        raise RuntimeError('Requires an assigned linked oncall worktree')
    # The shared main checkout, its index, config and main refs stay read-only.
    filesystem = {':root': 'read', str(worktree): 'write',
                  str(worktree / '.git'): 'read',
                  str(worktree / '.agents'): 'read',
                  str(worktree / '.codex'): 'read',
                  str(worktree / '.aws'): 'read',
                  str(gitdir): 'write', str(common / 'objects'): 'write',
                  str(common / 'refs/heads/oncall'): 'write',
                  str(common / 'logs/refs/heads/oncall'): 'write'}
    # TOML inline table keys/values are JSON-compatible strings.
    table = '{' + ', '.join(json.dumps(k) + '=' + json.dumps(v) for k, v in filesystem.items()) + '}'
    return ['codex', 'exec', '--ignore-user-config',
            '-c', 'default_permissions="oncall-local"',
            '-c', 'permissions.oncall-local.filesystem=' + table,
            '-c', 'permissions.oncall-local.network.enabled=false',
            '-c', 'approval_policy="never"', '-']


if __name__ == '__main__':
    args = command()
    gitdir = Path(git('rev-parse', '--absolute-git-dir')).resolve()
    scratch = gitdir / 'oncall-tmp'
    scratch.mkdir(exist_ok=True)
    env = os.environ.copy()
    env['TMPDIR'] = str(scratch)
    # Apple's /usr/bin/git shim uses a global cache outside this narrow policy.
    # Resolve the already-installed developer-tool binary; install nothing.
    if sys.platform == 'darwin' and shutil.which('git') == '/usr/bin/git':
        actual = subprocess.check_output(['xcrun', '--find', 'git'], text=True).strip()
        bindir = scratch / 'bin'
        bindir.mkdir(exist_ok=True)
        link = bindir / 'git'
        if not link.exists():
            link.symlink_to(actual)
        env['PATH'] = str(bindir) + os.pathsep + env['PATH']
    count = int(env.get('GIT_CONFIG_COUNT', '0'))
    env.update({f'GIT_CONFIG_KEY_{count}': 'gc.auto', f'GIT_CONFIG_VALUE_{count}': '0',
                f'GIT_CONFIG_KEY_{count + 1}': 'maintenance.auto', f'GIT_CONFIG_VALUE_{count + 1}': 'false',
                'GIT_CONFIG_COUNT': str(count + 2)})
    sys.exit(subprocess.call(args, stdin=sys.stdin, env=env))
