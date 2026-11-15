import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('promotion', Path(__file__).parents[1] / 'promote_production.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SHA = 'a' * 40


class Fake(m.Promotion):
    def __init__(self):
        super().__init__({k: v for k, v in {
            'CONFIRM': 'true', 'RENDER_API_KEY': 'secret', 'RENDER_DEV_SERVICE_ID': 'dev',
            'RENDER_PROD_SERVICE_ID': 'srv-prod', 'RENDER_PROD_DEPLOY_HOOK_URL': 'https://api.render.com/deploy/srv-prod?key=secret',
            'GH_TOKEN': 'token', 'GITHUB_REPOSITORY': 'owner/repo', 'DEV_URL': 'https://dev.example',
            'PROD_URL': 'https://prod.example'}.items()})
        self.mode = ''
        self.tags = 0
        self.requests = []

    def api(self, path, render=False, deadline=None):
        if 'jobs?' in path:
            return {'total_count': 3, 'jobs': [{'name': n, 'status': 'completed', 'conclusion': 'success'} for n in ('backend', 'frontend', 'stack')]}
        if self.mode == 'missing':
            return {'workflow_runs': []}
        run = {'head_sha': SHA, 'name': 'CI', 'run_number': 1, 'run_attempt': 2, 'id': 1,
               'status': 'in_progress' if self.mode == 'pending' else 'completed',
               'conclusion': 'failure' if self.mode == 'failed' else 'success', 'html_url': 'https://github.com/owner/repo/actions/runs/1', 'updated_at': '2026-11-15T10:00:00Z'}
        older = dict(run, conclusion='success', status='completed', run_number=2, updated_at='2026-11-14T10:00:00Z')
        return {'workflow_runs': [older, run]}

    def deploys(self, service, deadline=None):
        if service == 'dev':
            return [{'id': 'dep-dev', 'status': 'live', 'commit': {'id': SHA}},
                    {'id': 'dep-new', 'status': 'build_in_progress', 'commit': {'id': 'b'*40}}]
        if not self.hook_calls:
            return [{'id': 'dep-old', 'status': 'live', 'commit': {'id': SHA}}]
        return [{'id': 'dep-new', 'status': 'live', 'trigger': 'deploy_hook',
                 'commit': {'id': 'b'*40 if self.mode == 'wrong_sha' else SHA}}]

    def healthy(self, origin, deadline):
        if self.mode == 'unhealthy' and origin == self.env['DEV_URL']:
            raise m.Failure('Application /docs unhealthy')

    def request(self, url, token=None, method='GET', deadline=None):
        self.requests.append(url)
        if method == 'POST':
            if self.mode == 'hook_error':
                return 500, '', b''
            return 200, 'application/json', b'{"deploy":{"id":"dep-new"}}'
        if url.endswith('/api/auth/me'):
            return 401, 'application/json', b'{"code":"unauthorized","message":"Authentication required"}'
        return (503 if self.mode == 'smoke' else 200), 'text/html', b''


class Tests(unittest.TestCase):
    def fail_closed(self, mode, calls):
        p = Fake()
        p.mode = mode
        with self.assertRaises(m.Failure):
            p.run()
        self.assertEqual(p.hook_calls, calls)
        self.assertEqual(p.tag, '')
        return p

    def test_confirmation_false_no_network(self):
        p = Fake()
        p.env['CONFIRM'] = 'false'
        with self.assertRaises(m.Failure):
            p.run()
        self.assertEqual(p.requests, [])
        self.assertEqual(p.hook_calls, 0)
        self.assertEqual(p.tag, '')

    def test_preflight_failures_zero_hook_calls(self):
        for mode in ('missing', 'pending', 'failed', 'unhealthy'):
            with self.subTest(mode=mode):
                self.fail_closed(mode, 0)

    def test_hook_wrong_sha_smoke_failures_no_tag(self):
        for mode in ('hook_error', 'wrong_sha', 'smoke'):
            with self.subTest(mode=mode):
                self.fail_closed(mode, 1)

    def test_600_second_deadline(self):
        p = Fake()
        p.sha = SHA
        p.deploy_id = 'dep-missing'
        p.hook_calls = 1
        now = [0]
        def sleep(seconds):
            now[0] += seconds
        with patch.object(m.time, 'monotonic', side_effect=lambda: now[0]), patch.object(m.time, 'sleep', side_effect=sleep):
            with self.assertRaisesRegex(m.Failure, 'timeout'):
                p.poll(600, {'dep-old'})
        self.assertEqual(now[0], 600)
        self.assertEqual(p.tag, '')

    def test_queued_response_excludes_old_deployment(self):
        p = Fake()
        p.sha = SHA
        p.hook_calls = 1
        p.poll(m.time.monotonic() + 10, {'dep-old'})
        self.assertEqual(p.deploy_id, 'dep-new')

    def test_frozen_sha_and_preserved_hook_query(self):
        p = self.fail_closed('smoke', 1)
        self.assertEqual(p.sha, SHA)
        self.assertIn('key=secret&ref=' + SHA, p.requests[0])

    def test_summary_untrusted_note(self):
        import tempfile
        p = Fake()
        with tempfile.NamedTemporaryFile() as f:
            p.env.update(GITHUB_STEP_SUMMARY=f.name, DISPATCH_NOTE='<script>$(touch /tmp/bad)</script> @all')
            p.summary('rejected')
            content = Path(f.name).read_text()
        self.assertNotIn('<script>', content)
        self.assertNotIn('$(touch', content)
        self.assertNotIn('@all', content)


if __name__ == '__main__':
    unittest.main()
