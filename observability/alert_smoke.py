"""Local repeated-invalid-request drill, bounded traffic and resolution checks."""
import argparse
import json
import time
import urllib.error
import urllib.parse

import smoke


def fail():
    try:
        smoke.request(smoke.BASE + '/api/generate', b'')
    except urllib.error.HTTPError as error:
        assert error.code == 422, error.code
    else:
        raise AssertionError('Missing upload should fail with 422')


def alerts(environment, version):
    result = smoke.request('http://localhost:9090/api/v1/alerts')
    return [a for a in result['data']['alerts']
            if a['labels'].get('alertname') == 'GradeMatchGenerateFailures'
            and a['labels'].get('environment') == environment
            and a['labels'].get('version') == version]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default=smoke.BASE)
    parser.add_argument('--environment', default='local')
    parser.add_argument('--version', default='dev')
    args = parser.parse_args()
    smoke.BASE = args.base
    rules = smoke.request('http://localhost:9090/api/v1/rules')
    assert any(r['name'] == 'GradeMatchGenerateFailures' for g in rules['data']['groups'] for r in g['rules'])
    assert not alerts(args.environment, args.version), 'Start after prior alert resolves'
    smoke.stamp('rule loaded; baseline missing-upload request -> 422')
    fail()
    # Establish a counter sample before creating increments, including on a fresh stack.
    time.sleep(15)
    deadline = time.monotonic() + 240
    previous = None
    while True:
        fail()
        current = alerts(args.environment, args.version)
        state = current[0]['state'] if current else 'inactive'
        if state != previous:
            smoke.stamp('alert state=' + state)
            previous = state
        if state == 'firing':
            alert = current[0]
            for key, value in {'service': 'gradematch', 'owner': 'gradematch-maintainers',
                               'environment': args.environment, 'version': args.version}.items():
                assert alert['labels'][key] == value, alert
            assert alert['activeAt']
            expected = 'http://localhost:3000/d/gradematch/gradematch?' + urllib.parse.urlencode({
                'var-environment': args.environment, 'var-version': args.version})
            assert alert['annotations']['dashboard_url'] == expected, alert
            smoke.stamp('firing evidence=' + json.dumps(alert, sort_keys=True))
            break
        if time.monotonic() >= deadline:
            raise RuntimeError('Alert did not fire within 240s after baseline')
        time.sleep(10)
    smoke.stamp('traffic stopped; waiting at most 360s for rolling window to clear')
    smoke.poll(lambda: not alerts(args.environment, args.version), timeout=360)
    smoke.stamp('PASS: alert resolved (no matching alert in /api/v1/alerts)')


if __name__ == '__main__':
    main()
