"""Exercise both demo instances and assert real metrics/logs/traces and filters."""
import json
import os
from pathlib import Path
import time
import urllib.parse
import urllib.request

import dashboard_smoke
import smoke

PROM = 'http://localhost:19090'
LOKI = 'http://localhost:13100'
TEMPO = 'http://localhost:13200'
GRAFANA = 'http://localhost:13000'
PAIRS = [('dev', os.environ['DEMO_DEV_VERSION'], 18091),
         ('prod', os.environ['DEMO_PROD_VERSION'], 18092)]


def query(expression):
    result = smoke.request(PROM + '/api/v1/query?' + urllib.parse.urlencode({'query': expression}))
    assert result['status'] == 'success', result
    return result['data']['result']


def verify_pair(environment, version):
    selector = f'{{environment="{environment}",version="{version}"}}'
    rows = query('gradematch_styles_generated_total' + selector)
    assert rows and all(float(r['value'][1]) > 0 for r in rows), rows
    for row in rows:
        assert row['metric']['deployment_environment'] == environment
        assert row['metric']['service_version'] == version
    panels = {}
    for title, expression in dashboard_smoke.queries(environment, version):
        data = query(expression)
        assert data and all(float(r['value'][1]) > 0 for r in data), (title, data)
        panels[title] = data
    log_query = (f'{{service_name="gradematch",deployment_environment="{environment}",'
                 f'service_version="{version}"}} |= "API request completed"')
    logs = smoke.request(LOKI + '/loki/api/v1/query_range?' + urllib.parse.urlencode({
        'query': log_query, 'start': time.time_ns() - 600_000_000_000,
        'end': time.time_ns(), 'limit': 100}))['data']['result']
    assert logs, 'No matching logs'
    for stream in logs:
        assert stream['stream']['deployment_environment'] == environment
        assert stream['stream']['service_version'] == version
        for entry in stream['values']:
            metadata = entry[2] if len(entry) > 2 else {}
            trace_id = metadata.get('trace_id') or stream['stream'].get('trace_id')
            if not trace_id or int(trace_id, 16) == 0:
                continue
            trace = smoke.request(TEMPO + '/api/traces/' + trace_id)
            batches = trace.get('batches', trace.get('resourceSpans', []))
            for batch in batches:
                attrs = {a['key']: a['value'].get('stringValue') for a in batch['resource']['attributes']}
                assert attrs['deployment.environment'] == environment, attrs
                assert attrs['service.version'] == version, attrs
            assert batches
            return {'metric_query': 'gradematch_styles_generated_total' + selector,
                    'metrics': rows, 'panels': panels, 'log_query': log_query,
                    'log_streams': len(logs), 'trace_id': trace_id,
                    'trace_resource': {'deployment.environment': environment, 'service.version': version}}
    raise AssertionError('No correlated trace')


def main():
    smoke.poll(lambda: smoke.request(GRAFANA + '/api/health'))
    for iteration in range(2):
        for environment, version, port in PAIRS:
            smoke.BASE = f'http://localhost:{port}'
            dashboard_smoke.traffic(f'demo {environment} {version}')
        if iteration == 0:
            time.sleep(15)  # Counters need two scrapes before rate panels have data.
    evidence = {'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'instances': {}}
    for environment, version, _ in PAIRS:
        evidence['instances'][environment] = smoke.poll(lambda: verify_pair(environment, version))
    selections = [('dev', [PAIRS[0][1]], {'dev'}), ('prod', [PAIRS[1][1]], {'prod'}),
                  ('dev|prod', [p[1] for p in PAIRS], {'dev', 'prod'})]
    evidence['filters'] = {}
    for environment, versions, expected in selections:
        expression = ('gradematch_styles_generated_total{environment=~"' + environment +
                      '",version=~"' + '|'.join(versions) + '"}')
        rows = query(expression)
        assert {r['metric']['environment'] for r in rows} == expected, rows
        assert {r['metric']['version'] for r in rows} == set(versions), rows
        evidence['filters'][environment] = {'query': expression, 'result': rows}
    for label, expected in [('environment', {'dev', 'prod'}), ('version', {p[1] for p in PAIRS})]:
        values = smoke.request(PROM + '/api/v1/label/' + label + '/values?' + urllib.parse.urlencode({
            'match[]': 'gradematch_styles_generated_total'}))['data']
        assert expected <= set(values), values
        evidence[label + '_options'] = values
    output = Path(os.environ.get('DEMO_EVIDENCE_PATH', '/tmp/gradematch-obs-demo-evidence.json'))
    output.write_text(json.dumps(evidence, indent=2) + '\n')
    smoke.stamp('PASS dual environment metrics, six panels, logs, traces and dev/prod/both filters; evidence=' + str(output))
    for environment, version, port in PAIRS:
        print(f'{environment} app http://localhost:{port}; Grafana {GRAFANA}/d/gradematch/gradematch?var-environment={environment}&var-version={version}&from=now-15m&to=now')


if __name__ == '__main__':
    main()
