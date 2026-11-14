import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('poller', Path(__file__).parents[1] / 'poller.py')
poller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(poller)


def alert(**labels):
    return {'state': 'firing', 'activeAt': '2026-11-14T00:00:00Z', 'labels': {'alertname': '../../Bad alert', 'owner': 'team', **labels}}


class PollerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-b', 'main')
        self.git('config', 'user.email', 'test@example.com')
        self.git('config', 'user.name', 'Test')
        (self.repo / 'file').write_text('clean')
        self.git('add', '.')
        self.git('commit', '-m', 'base')
        self.state = self.root / 'state'

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repo, text=True, stderr=subprocess.STDOUT).strip()

    def make(self, **kw):
        return poller.Poller(self.repo, self.state, 'http://localhost/alerts', ['python3', str(self.root / 'agent.py')], **kw)

    def join(self, p):
        for thread in p.threads:
            thread.join(10)
            self.assertFalse(thread.is_alive())

    def test_identity_complete_sorted(self):
        a = alert()
        b = dict(a, labels=dict(reversed(list(a['labels'].items()))))
        self.assertEqual(poller.identity(a), poller.identity(b))
        self.assertNotEqual(poller.identity(a), poller.identity(alert(extra='new')))
        self.assertNotEqual(poller.identity(a), poller.identity(dict(a, activeAt='later')))

    def test_dry_run_has_no_effects(self):
        before = self.git('show-ref')
        with patch.object(poller.subprocess, 'Popen', side_effect=AssertionError('process')):
            self.make(dry_run=True).dispatch(alert())
        self.assertFalse(self.state.exists())
        self.assertEqual(before, self.git('show-ref'))

    def test_slow_agent_restart_collision_dirty_no_push(self):
        (self.root / 'agent.py').write_text("import sys,time,subprocess\nsys.stdin.read()\ntime.sleep(.2)\nprint('Bearer super-secret')\nsubprocess.run(['git','status','--short'],check=True)\n")
        original = self.git('rev-parse', 'HEAD')
        (self.repo / 'file').write_text('dirty')
        p = self.make(now=lambda: poller.datetime(2026, 11, 14, tzinfo=poller.timezone.utc))
        # Record every launcher/agent Git invocation through a PATH wrapper.
        real_git = subprocess.check_output(['which', 'git'], text=True).strip()
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        calls = self.root / 'git-calls'
        wrapper = bin_dir / 'git'
        wrapper.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{calls}"\nexec "{real_git}" "$@"\n')
        wrapper.chmod(0o755)
        import os
        with patch.dict(os.environ, PATH=str(bin_dir) + ':' + os.environ['PATH']):
            p.dispatch(alert())
            self.assertEqual(len(list(self.state.glob('*.claim'))), 1)
            for _ in range(3):
                self.make().dispatch(alert())
            self.join(p)
            p.dispatch(alert(extra='new'))
            self.join(p)
        self.assertEqual(len(list(self.state.glob('*.claim'))), 2)
        self.assertEqual((self.repo / 'file').read_text(), 'dirty')
        self.assertEqual(self.git('rev-parse', 'HEAD'), original)
        branches = self.git('branch', '--list', 'oncall/*').splitlines()
        self.assertEqual(len(branches), 2)
        self.assertTrue(any(line.endswith('-1') for line in branches))
        self.assertNotIn('push', calls.read_text())
        logs = '\n'.join(p.read_text() for p in self.state.glob('*.log'))
        self.assertIn('exit_status=0', logs)
        self.assertIn('local_fix_commit=none', logs)
        self.assertIn('investigation_result=no_new_commit', logs)
        self.assertNotIn('super-secret', logs)

    def test_real_new_local_commit_is_reported(self):
        (self.root / 'agent.py').write_text("import sys,subprocess\nsys.stdin.read()\nopen('fix','w').write('corrected')\nsubprocess.run(['git','add','fix'],check=True)\nsubprocess.run(['git','commit','-m','local fix'],check=True)\n")
        p = self.make()
        p.dispatch(alert())
        self.join(p)
        log = next(self.state.glob('*.log')).read_text()
        self.assertIn('investigation_result=local_commit_created', log)
        self.assertNotIn('local_fix_commit=none', log)
        self.assertEqual(self.git('branch', '--show-current'), 'main')

    def test_launch_failure_is_not_retried(self):
        p = self.make()
        p.agent = ['/no/such/agent']
        p.dispatch(alert())
        self.join(p)
        again = self.make()
        again.dispatch(alert())
        self.assertEqual(again.threads, [])
        self.assertIn('identity remains claimed', next(self.state.glob('*.log')).read_text())

    def test_nonzero_agent(self):
        (self.root / 'agent.py').write_text('import sys\nsys.stdin.read()\nsys.exit(7)\n')
        p = self.make()
        p.dispatch(alert())
        self.join(p)
        self.assertIn('exit_status=7', next(self.state.glob('*.log')).read_text())

    def test_poll_errors_and_firing_only(self):
        p = self.make()
        response = json.dumps({'status': 'success', 'data': {'alerts': [alert(), dict(alert(), state='pending')]}}).encode()
        with patch.object(poller.urllib.request, 'urlopen', return_value=io.BytesIO(response)), patch.object(p, 'dispatch') as dispatch:
            p.poll()
            dispatch.assert_called_once_with(alert())
        for result in [io.BytesIO(b'not json'), io.BytesIO(b'{"status":"success","data":{"alerts":[]}}')]:
            with patch.object(poller.urllib.request, 'urlopen', return_value=result):
                p.poll()
        with patch.object(poller.urllib.request, 'urlopen', side_effect=TimeoutError('timeout')):
            p.poll()
        self.assertIn('timeout', (self.state / 'poller.log').read_text())

    def test_immediate_sixty_second_cadence(self):
        p = self.make()
        events = []
        clock = [0]
        def sleep(seconds):
            events.append(('sleep', seconds))
            clock[0] += seconds
            if clock[0] >= 120:
                raise KeyboardInterrupt
        with patch.object(p, 'poll', side_effect=lambda: events.append(('poll', clock[0]))), patch.object(poller.time, 'monotonic', side_effect=lambda: clock[0]):
            with self.assertRaises(KeyboardInterrupt):
                p.run(sleep)
        self.assertEqual(events, [('poll', 0), ('sleep', 60), ('poll', 60), ('sleep', 60)])

    def test_credentials(self):
        text = poller.redact('http://alice:secret@host token=abc password:xyz Bearer abc.def')
        for secret in ['alice', 'secret@', 'abc', 'xyz']:
            self.assertNotIn(secret, text)


if __name__ == '__main__':
    unittest.main()
