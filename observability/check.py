"""Check real readiness and provisioning; no external Python dependencies."""
import base64
import json
import os
import time
import urllib.request


def get(url, headers=None):
    for attempt in range(31):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=3) as response:
                return response.read()
        except Exception:
            if attempt == 30:
                raise
            time.sleep(3)


if __name__ == '__main__':
    for name, path in [('collector', '13133/'), ('prometheus', '9090/-/ready'),
                       ('loki', '3100/ready'), ('tempo', '3200/ready'),
                       ('grafana', '3000/api/health')]:
        get('http://localhost:' + path)
        print(name + ': ready')
    credentials = 'admin:' + os.getenv('GRAFANA_PASSWORD', 'admin')
    headers = {'Authorization': 'Basic ' + base64.b64encode(credentials.encode()).decode()}
    sources = json.loads(get('http://localhost:3000/api/datasources', headers))
    assert {s['uid'] for s in sources} >= {'prometheus', 'loki', 'tempo'}
    for uid in ('prometheus', 'loki', 'tempo'):
        if uid == 'tempo':
            # Tempo 11.6 uses a frontend health check; backend CheckHealth is absent.
            assert get('http://localhost:3000/api/datasources/proxy/uid/tempo/ready', headers).strip() == b'ready'
        else:
            result = json.loads(get(f'http://localhost:3000/api/datasources/uid/{uid}/health', headers))
            assert result['status'] == 'OK', result
        print(uid + ': provisioned, health OK')

    dashboard = json.loads(get('http://localhost:3000/api/dashboards/uid/gradematch', headers))
    assert dashboard['meta']['provisioned']
    assert dashboard['dashboard']['uid'] == 'gradematch'
    assert dashboard['meta']['url'] == '/d/gradematch/gradematch'
    assert len(dashboard['dashboard']['panels']) >= 6
    print('gradematch: dashboard provisioned, stable URL, six panels')
