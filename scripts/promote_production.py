"""Fail-closed manual promotion; standard library only. Never log raw responses."""
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


class Failure(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Promotion:
    def __init__(self, env=None):
        self.env = os.environ if env is None else env
        self.started = dt.datetime.now(dt.timezone.utc)
        self.clock_start = time.monotonic()
        self.sha = self.tag = self.ci_url = self.deploy_id = ''
        self.hook_calls = 0
        self.opener = urllib.request.build_opener(NoRedirect)

    def request(self, url, token=None, method='GET', deadline=None):
        timeout = 20 if deadline is None else min(20, deadline - time.monotonic())
        if timeout <= 0:
            raise Failure('Deployment verification timeout')
        headers = {'Accept': 'application/json', 'User-Agent': 'GradeMatch-promotion'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        try:
            with self.opener.open(urllib.request.Request(url, headers=headers, method=method), timeout=timeout) as r:
                return r.status, r.headers.get('Content-Type', ''), r.read()
        except urllib.error.HTTPError as e:
            # Expected errors (notably auth smoke HTTP 401) still carry the
            # application contract. Keep a bounded body in memory, never log it.
            try:
                body = e.read(1024 * 1024)
            except Exception:
                raise Failure('HTTP error response read failed') from None
            finally:
                e.close()
            return e.code, e.headers.get('Content-Type', ''), body
        except Exception:
            raise Failure('HTTP transport failed') from None

    def api(self, path, render=False, deadline=None):
        base = 'https://api.render.com/v1' if render else 'https://api.github.com'
        token = self.env['RENDER_API_KEY' if render else 'GH_TOKEN']
        status, _, body = self.request(base + path, token, deadline=deadline)
        if status != 200:
            raise Failure('Metadata request HTTP ' + str(status))
        try:
            return json.loads(body)
        except Exception:
            raise Failure('Invalid metadata JSON') from None

    def deploys(self, service, deadline=None):
        rows, cursor = [], ''
        for _ in range(100):
            path = '/services/' + urllib.parse.quote(service, safe='') + '/deploys?limit=100'
            if cursor:
                path += '&cursor=' + urllib.parse.quote(cursor, safe='')
            page = self.api(path, True, deadline)
            if not isinstance(page, list):
                raise Failure('Invalid deployment list')
            rows.extend(item['deploy'] for item in page)
            if len(page) < 100:
                return rows
            next_cursor = page[-1].get('cursor')
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
        raise Failure('Deployment pagination incomplete')

    def ci(self):
        repo = self.env['GITHUB_REPOSITORY']
        runs = self.api(f'/repos/{repo}/actions/workflows/ci.yml/runs?head_sha={self.sha}&per_page=100')['workflow_runs']
        runs = [r for r in runs if r['head_sha'] == self.sha and r['name'] == 'CI']
        if not runs:
            raise Failure('CI missing for frozen SHA')
        run = max(runs, key=lambda r: (r.get('updated_at', ''), r['run_number'], r['run_attempt']))
        if run['status'] != 'completed' or run['conclusion'] != 'success':
            raise Failure('Latest CI is not completed successfully')
        jobs = self.api(f"/repos/{repo}/actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs?per_page=100")
        if jobs['total_count'] > 100:
            raise Failure('CI job list incomplete')
        for name in ('backend', 'frontend', 'stack'):
            found = [j for j in jobs['jobs'] if j['name'] == name]
            if len(found) != 1 or found[0]['status'] != 'completed' or found[0]['conclusion'] != 'success':
                raise Failure('Required CI job not successful: ' + name)
        self.ci_url = run['html_url']
        print('CI: ' + self.ci_url)

    def healthy(self, origin, deadline):
        while time.monotonic() < deadline:
            try:
                status, _, body = self.request(origin + '/docs', deadline=deadline)
                if status == 200 and b'SwaggerUIBundle' in body:
                    return
            except Failure:
                pass
            time.sleep(min(5, max(0, deadline - time.monotonic())))
        raise Failure('Application /docs unhealthy or timeout')

    def poll(self, deadline, baseline):
        terminal = {'build_failed', 'update_failed', 'pre_deploy_failed', 'canceled', 'deactivated'}
        while time.monotonic() < deadline:
            rows = self.deploys(self.env['RENDER_PROD_SERVICE_ID'], deadline)
            if self.deploy_id:
                matching = [d for d in rows if d['id'] == self.deploy_id]
            else:
                matching = [d for d in rows if d['id'] not in baseline and d.get('trigger') == 'deploy_hook'
                            and d.get('commit', {}).get('id') == self.sha]
            if len(matching) > 1:
                raise Failure('Ambiguous production deployment')
            if matching:
                deploy = matching[0]
                if deploy.get('commit', {}).get('id') != self.sha:
                    raise Failure('Production SHA mismatch')
                self.deploy_id = deploy['id']
                if deploy['status'] in terminal:
                    raise Failure('Production deployment failed')
                if deploy['status'] == 'live':
                    self.healthy(self.env['PROD_URL'], deadline)
                    print('Render production deploy: ' + self.deploy_id)
                    return
            time.sleep(min(5, max(0, deadline - time.monotonic())))
        raise Failure('Deployment verification timeout')

    def smoke(self):
        for path in ('/', '/login', '/docs', '/api/auth/me'):
            status, content_type, body = self.request(self.env['PROD_URL'] + path)
            print(f'Smoke {path}: {status}')
            if status != (401 if path == '/api/auth/me' else 200):
                raise Failure('Smoke status mismatch')
            if path == '/api/auth/me':
                if content_type.split(';')[0].strip().lower() != 'application/json':
                    raise Failure('Smoke JSON content type mismatch')
                try:
                    data = json.loads(body)
                    valid = isinstance(data, dict) and all(isinstance(data.get(k), str) and data[k].strip() for k in ('code', 'message'))
                except Exception:
                    valid = False
                if not valid:
                    raise Failure('Smoke error contract mismatch')

    def run(self):
        if self.env.get('CONFIRM') != 'true':
            raise Failure('Confirmation rejected; zero deployment calls')
        for key in ('RENDER_API_KEY', 'RENDER_DEV_SERVICE_ID', 'RENDER_PROD_DEPLOY_HOOK_URL',
                    'RENDER_PROD_SERVICE_ID', 'DEV_URL', 'PROD_URL', 'GH_TOKEN', 'GITHUB_REPOSITORY'):
            if not self.env.get(key):
                raise Failure('Missing configuration: ' + key)
        for key in ('DEV_URL', 'PROD_URL'):
            p = urllib.parse.urlsplit(self.env[key])
            if p.scheme != 'https' or not p.netloc or p.username or p.password or p.query or p.fragment or p.path not in ('', '/'):
                raise Failure('Invalid public origin configuration')
            self.env[key] = self.env[key].rstrip('/')
        live = [d for d in self.deploys(self.env['RENDER_DEV_SERVICE_ID']) if d.get('status') == 'live']
        if len(live) != 1:
            raise Failure('Absent or ambiguous live dev deploy')
        self.sha = live[0].get('commit', {}).get('id', '')
        if not re.fullmatch('[0-9a-f]{40}', self.sha):
            raise Failure('Invalid dev commit SHA')
        print('Frozen dev SHA: ' + self.sha)
        self.ci()
        self.healthy(self.env['DEV_URL'], time.monotonic() + 120)
        baseline = {d['id'] for d in self.deploys(self.env['RENDER_PROD_SERVICE_ID'])}
        hook = urllib.parse.urlsplit(self.env['RENDER_PROD_DEPLOY_HOOK_URL'])
        if hook.scheme != 'https' or hook.hostname != 'api.render.com' or hook.username or hook.password or hook.fragment or hook.path != '/deploy/' + self.env['RENDER_PROD_SERVICE_ID']:
            raise Failure('Invalid deploy hook configuration')
        query = urllib.parse.parse_qsl(hook.query, keep_blank_values=True)
        if any(k == 'ref' for k, _ in query):
            raise Failure('Hook must not contain a preconfigured ref')
        url = urllib.parse.urlunsplit(hook._replace(query=urllib.parse.urlencode(query + [('ref', self.sha)])))
        deadline = time.monotonic() + 600
        self.hook_calls += 1
        status, _, body = self.request(url, method='POST', deadline=deadline)
        if status == 200:
            try:
                self.deploy_id = json.loads(body)['deploy']['id']
                if not isinstance(self.deploy_id, str) or not re.fullmatch('dep-[a-z0-9]+', self.deploy_id):
                    raise ValueError()
            except Exception:
                raise Failure('Invalid deploy hook response') from None
        elif status != 202:
            raise Failure('Deploy hook HTTP ' + str(status))
        self.poll(deadline, baseline)
        self.smoke()
        tag = 'prod-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d-%H%M%S-') + self.sha[:7]
        # GitHub creates the ref atomically and rejects an existing tag (422).
        repo = self.env['GITHUB_REPOSITORY']
        payload = json.dumps({'ref': 'refs/tags/' + tag, 'sha': self.sha}).encode()
        req = urllib.request.Request(f'https://api.github.com/repos/{repo}/git/refs', data=payload,
                                     headers={'Authorization': 'Bearer ' + self.env['GH_TOKEN'], 'Content-Type': 'application/json'}, method='POST')
        try:
            with self.opener.open(req, timeout=20) as r:
                if r.status != 201:
                    raise Failure('Tag creation failed')
        except Exception:
            raise Failure('Tag creation failed or collision; no overwrite attempted') from None
        self.tag = tag

    def summary(self, outcome):
        ended = dt.datetime.now(dt.timezone.utc)
        fields = {'Outcome': outcome, 'Commit SHA': self.sha, 'Dev URL': self.env.get('DEV_URL', ''),
                  'Prod URL': self.env.get('PROD_URL', ''), 'UTC start': self.started.isoformat(),
                  'UTC end': ended.isoformat(), 'Elapsed seconds': str(round(time.monotonic() - self.clock_start, 1)),
                  'Dispatch note': self.env.get('DISPATCH_NOTE', ''), 'Tag': self.tag, 'CI': self.ci_url,
                  'Render deploy ID': self.deploy_id, 'Deployment calls': str(self.hook_calls)}
        # Numeric character references prevent Markdown, HTML and mention execution.
        def safe(value):
            for key in ('RENDER_API_KEY', 'RENDER_PROD_DEPLOY_HOOK_URL', 'GH_TOKEN'):
                secret = self.env.get(key)
                if secret:
                    value = value.replace(secret, '[redacted]')
            return ''.join(f'&#{ord(c)};' for c in value)
        result = '\n'.join(f'<p><strong>{html.escape(k)}:</strong> {safe(v)}</p>' for k, v in fields.items())
        if self.hook_calls and not self.tag:
            result += '\n<p>Post-deploy failure may leave the promoted version live. No rollback was attempted.</p>'
        if self.env.get('GITHUB_STEP_SUMMARY'):
            with open(self.env['GITHUB_STEP_SUMMARY'], 'a') as f:
                f.write(result + '\n')
        print('Deployment calls: ' + str(self.hook_calls))


def main():
    promotion = Promotion()
    outcome, code = 'success', 0
    try:
        promotion.run()
    except Failure as e:
        outcome, code = str(e), 1
        print(outcome)
    except Exception:
        outcome, code = 'Unexpected promotion failure (details suppressed)', 1
        print(outcome)
    finally:
        promotion.summary(outcome)
    return code


if __name__ == '__main__':
    sys.exit(main())
