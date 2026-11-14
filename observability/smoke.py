"""Real register/generate/save smoke. Prints identifiers, never credentials/payloads."""
import datetime
import json
from pathlib import Path
import secrets
import time
import urllib.parse
import urllib.request

BASE = 'http://localhost:8091'
SELECTOR = '{service_name="gradematch",deployment_environment="local",service_version="dev"}'
METRICS = ('styles_generated', 'looks_saved', 'users_registered')


def stamp(message):
    print(datetime.datetime.now(datetime.timezone.utc).isoformat() + ' ' + message, flush=True)


def request(url, data=None, headers=None, status=200):
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers or {}), timeout=30) as r:
        assert r.status == status, (url, r.status)
        return json.loads(r.read())


def poll(fn, timeout=90):
    deadline = time.monotonic() + timeout
    while True:
        try:
            value = fn()
            if value:
                return value
        except (OSError, ValueError, AssertionError):
            pass
        if time.monotonic() >= deadline:
            raise RuntimeError('Timed out waiting for telemetry; check stack logs')
        time.sleep(2)


def metrics():
    values = {}
    for name in METRICS:
        query = f'gradematch_{name}_total{{environment="local",version="dev"}}'
        result = request('http://localhost:9090/api/v1/query?' + urllib.parse.urlencode({'query': query}))
        values[name] = sum(float(row['value'][1]) for row in result['data']['result'])
    return values


def journey(label):
    # Unique throwaway credentials exist only in process memory; never print them.
    auth = request(BASE + '/api/auth/register', json.dumps({
        'email': 'obs-' + secrets.token_hex(12) + '@example.com',
        'password': secrets.token_urlsafe(24),
    }).encode(), {'Content-Type': 'application/json'}, 201)
    stamp(label + ' POST /api/auth/register -> 201')
    headers = {'Authorization': 'Bearer ' + auth['access_token']}
    boundary = 'GradeMatch' + secrets.token_hex(16)
    fixture = Path(__file__).resolve().parents[1] / 'e2e/fixtures/reference-warm.jpg'
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="referenceFile"; filename="reference.jpg"\r\n'
            'Content-Type: image/jpeg\r\n\r\n').encode() + fixture.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
    style = request(BASE + '/api/generate', body, {**headers, 'Content-Type': 'multipart/form-data; boundary=' + boundary})
    stamp(label + ' POST /api/generate -> 200 style_id=' + style['id'])
    look = request(BASE + '/api/looks', json.dumps({
        'name': 'Observability smoke', 'styleParams': style,
        'adjustments': {'intensity': 100, 'contrast': 0, 'saturation': 0, 'warmth': 0},
        'thumbnail': '',
    }).encode(), {**headers, 'Content-Type': 'application/json'}, 201)
    stamp(label + ' POST /api/looks -> 201 look_id=' + look['id'])


def main():
    stamp('command: python3 observability/smoke.py')
    # Establish series even on a fresh installation, then measure a second journey.
    journey('baseline')
    # Let an app restart's counter reset reach Collector and the next scrape.
    time.sleep(12)
    def initialized():
        value = metrics()
        return value if all(value.values()) else None
    before = poll(initialized)
    stamp('metrics before=' + json.dumps(before, sort_keys=True))
    start = time.time_ns()
    journey('scenario')
    def incremented():
        value = metrics()
        return value if all(value[k] >= before[k] + 1 for k in METRICS) else None
    after = poll(incremented)
    stamp('metrics after=' + json.dumps(after, sort_keys=True))
    query = SELECTOR + ' |= "API request completed"'
    def find():
        end = time.time_ns()
        result = request('http://localhost:3100/loki/api/v1/query_range?' + urllib.parse.urlencode({
            'query': query, 'start': start, 'end': end, 'limit': 100}))
        for stream in result['data']['result']:
            for entry in stream['values']:
                metadata = entry[2] if len(entry) > 2 else {}
                trace_id = metadata.get('trace_id') or stream['stream'].get('trace_id')
                if not trace_id or int(trace_id, 16) == 0:
                    continue
                trace = request('http://localhost:3200/api/traces/' + trace_id)
                batches = trace.get('batches', trace.get('resourceSpans', []))
                for batch in batches:
                    attrs = {a['key']: a['value'].get('stringValue') for a in batch['resource']['attributes']}
                    assert attrs['service.name'] == 'gradematch'
                    assert attrs['deployment.environment'] == 'local'
                    assert attrs['service.version'] == 'dev'
                    for scope in batch.get('scopeSpans', []):
                        if any(s['name'] == 'POST /api/generate' for s in scope['spans']):
                            return trace_id, entry[0], end
        return None
    trace_id, log_ns, end = poll(find)
    stamp('Loki query=' + query + f' start={start} end={end} log_timestamp_ns={log_ns} trace_id={trace_id}')
    stamp('Tempo GET /api/traces/' + trace_id + ' -> 200; service=gradematch environment=local version=dev; span=POST /api/generate')
    stamp('Grafana http://localhost:3000/explore?left=' + urllib.parse.quote(json.dumps({
        'datasource': 'tempo', 'queries': [{'refId': 'A', 'queryType': 'traceql', 'query': trace_id}]})))
    stamp('PASS: metrics increment and log/trace IDs match')


if __name__ == '__main__':
    main()
