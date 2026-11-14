"""Populate all six panels and check their exact provisioned PromQL, using stdlib."""
import argparse
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse

import smoke


def queries(environment, version):
    dashboard = json.loads((Path(__file__).parent / 'grafana/dashboards/gradematch.json').read_text())
    for panel in dashboard['panels']:
        expression = panel['targets'][0]['expr'].replace('$__rate_interval', '1m')
        expression = expression.replace('$environment', environment).replace('$version', version)
        yield panel['title'], expression


def traffic(label):
    settings = smoke.journey(label)
    smoke.request(smoke.BASE + '/api/render-lut', json.dumps(settings).encode(), {'Content-Type': 'application/json'})
    try:
        smoke.request(smoke.BASE + '/api/generate', b'')
    except urllib.error.HTTPError as error:
        assert error.code == 422, error.code
    else:
        raise AssertionError('Missing upload should be rejected')
    smoke.stamp(label + ' render -> 200; missing generate -> 422')


def check(environment, version):
    values = {}
    for title, expression in queries(environment, version):
        result = smoke.request('http://localhost:9090/api/v1/query?' + urllib.parse.urlencode({'query': expression}))
        assert result['status'] == 'success', result
        rows = result['data']['result']
        assert rows and all(float(r['value'][1]) > 0 for r in rows), (title, rows)
        values[title] = rows
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default=smoke.BASE)
    parser.add_argument('--environment', default='local')
    parser.add_argument('--version', default='dev')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    smoke.BASE = args.base
    if not args.check_only:
        traffic('dashboard baseline')
        time.sleep(15)
        traffic('dashboard scenario')
    result = smoke.poll(lambda: check(args.environment, args.version))
    smoke.stamp('all six provisioned queries nonempty: ' + json.dumps(result, sort_keys=True))
    smoke.stamp('http://localhost:3000/d/gradematch/gradematch?' + urllib.parse.urlencode({
        'var-environment': args.environment, 'var-version': args.version, 'from': 'now-15m', 'to': 'now'}))


if __name__ == '__main__':
    main()
