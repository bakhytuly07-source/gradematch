import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('codex_agent', Path(__file__).parents[1] / 'codex_agent.py')
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)


class ScopedPermissionsTests(unittest.TestCase):
    def test_only_assigned_metadata_and_oncall_refs_writable(self):
        with patch.object(agent, 'git', side_effect=['/repo/worker', '/repo/main/.git/worktrees/worker', '/repo/main/.git', 'oncall/test']):
            command = agent.command()
        text = ' '.join(command)
        self.assertIn('--ignore-user-config', command)
        self.assertNotIn('--sandbox', command)
        self.assertIn('default_permissions="oncall-local"', command)
        self.assertIn('"/repo/main/.git/worktrees/worker"="write"', text)
        self.assertIn('"/repo/main/.git/objects"="write"', text)
        self.assertIn('"/repo/main/.git/refs/heads/oncall"="write"', text)
        self.assertNotIn('"/repo/main/.git"="write"', text)
        self.assertNotIn('refs/heads/main', text)
        self.assertIn('network.enabled=false', text)

    def test_rejects_main_or_nonlinked_checkout(self):
        for branch, gitdir in [('main', '/repo/.git/worktrees/w'), ('oncall/test', '/repo/.git')]:
            with patch.object(agent, 'git', side_effect=['/repo', gitdir, '/repo/.git', branch]):
                with self.assertRaises(RuntimeError):
                    agent.command()
