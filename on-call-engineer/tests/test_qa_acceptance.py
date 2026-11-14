"""QA checks for alert-instance renewal and durable pre-launch ordering."""
import test_poller
from test_poller import alert, poller
from unittest.mock import patch


class AcceptanceTests(test_poller.PollerTests):
    def test_new_active_time_launches_after_restart_and_claim_precedes_launch(self):
        (self.root / 'agent.py').write_text('import sys\nsys.stdin.read()\n')
        import subprocess
        real_popen = subprocess.Popen
        launches = []

        def inspect_claim(*args, **kwargs):
            command = args[0]
            if command[0] == 'python3':
                claims = list(self.state.glob('*.claim'))
                self.assertTrue(claims)
                self.assertTrue(all(p.read_text() for p in claims))
                launches.append(command)
            return real_popen(*args, **kwargs)

        with patch.object(poller.subprocess, 'Popen', side_effect=inspect_claim):
            first = self.make()
            first.dispatch(alert())
            self.join(first)
            restarted = self.make()
            restarted.dispatch(alert())
            self.assertEqual(restarted.threads, [])
            restarted.dispatch(dict(alert(), activeAt='2026-11-14T01:00:00Z'))
            self.join(restarted)
        self.assertEqual(len(launches), 2)
        self.assertEqual(len(list(self.state.glob('*.claim'))), 2)
