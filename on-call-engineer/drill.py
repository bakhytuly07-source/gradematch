"""Valid-image local drill traffic/checks; no branch/code changes or credentials."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import urllib.error
import urllib.request


def stamp(message):
    print(datetime.now(timezone.utc).isoformat() + ' ' + message, flush=True)


def generate(base):
    boundary = 'GradeMatchFaultDrill'
    fixture = Path(__file__).resolve().parents[1] / 'e2e/fixtures/reference-warm.jpg'
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="referenceFile"; filename="reference.jpg"\r\n'
            'Content-Type: image/jpeg\r\n\r\n').encode() + fixture.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
    request = urllib.request.Request(base + '/api/generate', data=body, headers={
        'Content-Type': 'multipart/form-data; boundary=' + boundary})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status
    except urllib.error.HTTPError as error:
        error.close()
        return error.code


def alerts(prometheus, environment, version):
    with urllib.request.urlopen(prometheus + '/api/v1/alerts', timeout=10) as response:
        payload = json.load(response)
    return [a for a in payload['data']['alerts'] if
            a['labels'].get('alertname') == 'GradeMatchGenerateFailures'
            and a['labels'].get('environment') == environment
            and a['labels'].get('version') == version]


def run(args):
    if args.mode == 'check':
        actual = generate(args.base)
        stamp(f'valid image generate status={actual} expected={args.expect}')
        if actual != args.expect:
            raise RuntimeError('Unexpected generation result')
        return
    deadline = time.monotonic() + (300 if args.mode == 'fire' else 360)
    if args.mode == 'fire':
        if alerts(args.prometheus, args.environment, args.version):
            raise RuntimeError('Wait for prior matching alert to resolve before starting')
        actual = generate(args.base)
        if actual != 500:
            raise RuntimeError(f'Expected injected valid-image failure 500, got {actual}')
        stamp('baseline 500; waiting 15s for initial counter export/scrape')
        time.sleep(15)
    while time.monotonic() < deadline:
        if args.mode == 'fire':
            actual = generate(args.base)
            if actual != 500:
                raise RuntimeError(f'Expected 500, got {actual}; stop faulty traffic once agent fix is ready')
        current = alerts(args.prometheus, args.environment, args.version)
        stamp('alerts=' + json.dumps(current, sort_keys=True))
        if args.mode == 'fire' and any(a['state'] == 'firing' for a in current):
            stamp('FIRING; traffic stopped; capture screenshot/API evidence and run poller')
            return
        if args.mode == 'resolve' and not current:
            stamp('RESOLVED; no matching alert in Prometheus alerts API')
            return
        time.sleep(10)
    raise RuntimeError('Timed out; inspect Collector/identity/rule health')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['check', 'fire', 'resolve'])
    parser.add_argument('--base', default='http://localhost:8092')
    parser.add_argument('--prometheus', default='http://localhost:9090')
    parser.add_argument('--environment', default='drill')
    parser.add_argument('--version', default='fault-drill')
    parser.add_argument('--expect', type=int, default=200)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
