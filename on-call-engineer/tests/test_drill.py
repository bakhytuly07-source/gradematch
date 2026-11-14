import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('drill', Path(__file__).parents[1] / 'drill.py')
drill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drill)


class DrillTests(unittest.TestCase):
    def args(self, mode):
        return SimpleNamespace(mode=mode, base='http://localhost:8092', prometheus='http://localhost:9090', environment='drill', version='fault-drill', expect=200)

    def test_valid_upload_and_status(self):
        response = io.BytesIO(b'{}')
        response.status = 200
        with patch.object(drill.urllib.request, 'urlopen', return_value=response) as call:
            self.assertEqual(drill.generate('http://localhost:8092'), 200)
        request = call.call_args.args[0]
        self.assertIn(b'name="referenceFile"', request.data)
        self.assertIn(b'\xff\xd8\xff', request.data)

    def test_check_enforces_before_after(self):
        with patch.object(drill, 'generate', return_value=500):
            with self.assertRaises(RuntimeError):
                drill.run(self.args('check'))
        with patch.object(drill, 'generate', return_value=200):
            drill.run(self.args('check'))

    def test_fire_baseline_and_stops_at_firing(self):
        args = self.args('fire')
        with patch.object(drill, 'alerts', side_effect=[[], [], [{'state': 'firing'}]]), patch.object(drill, 'generate', return_value=500) as generate, patch.object(drill.time, 'sleep') as sleep:
            drill.run(args)
        self.assertEqual(generate.call_count, 3)
        self.assertEqual([x.args[0] for x in sleep.call_args_list], [15, 10])

    def test_no_fault_traffic_during_resolution(self):
        with patch.object(drill, 'alerts', return_value=[]), patch.object(drill, 'generate') as generate:
            drill.run(self.args('resolve'))
        generate.assert_not_called()

    def test_identity_filter(self):
        wrong = {'labels': {'alertname': 'GradeMatchGenerateFailures', 'environment': 'other', 'version': 'fault-drill'}}
        correct = {'labels': {**wrong['labels'], 'environment': 'drill'}, 'activeAt': 'now'}
        payload = io.BytesIO(json.dumps({'data': {'alerts': [wrong, correct]}}).encode())
        with patch.object(drill.urllib.request, 'urlopen', return_value=payload):
            self.assertEqual(drill.alerts('http://localhost', 'drill', 'fault-drill'), [correct])
