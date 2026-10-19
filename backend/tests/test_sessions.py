from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from app.sessions import MemorySessions
from test_api import assert_schema


@pytest.mark.parametrize('authorization',[None,'','Bearer','Basic value','Bearer unknown','Bearer bad token'])
@pytest.mark.parametrize('path,method',[('/api/auth/me','get'),('/api/auth/logout','post')])
def test_invalid_bearer_rejected(memory_client,authorization,path,method):
    headers={} if authorization is None else {'Authorization':authorization}
    assert assert_schema(getattr(memory_client,method)(path,headers=headers),'Error',401)['code']=='auth'


def test_expiry_revocation_and_other_sessions_with_controlled_clock():
    time=[1000]
    sessions=MemorySessions(clock=lambda:time[0],ttl_ms=100)
    application=create_app(sessions=sessions)
    with TestClient(application) as client:
        first=client.post('/api/auth/register',json={'email':'a@example.com','password':'password123'}).json()
        second=client.post('/api/auth/login',json={'email':'a@example.com','password':'password123'}).json()
        outsider=client.post('/api/auth/register',json={'email':'b@example.com','password':'password123'}).json()
        header=lambda value:{'Authorization':'Bearer '+value['access_token']}
        assert client.get('/api/auth/me',headers=header(first)).json()==first['user']
        response=client.post('/api/auth/logout',headers=header(first))
        assert response.status_code==204 and response.content==b''
        for path,method in [('/api/auth/me','get'),('/api/auth/logout','post')]:
            assert_schema(getattr(client,method)(path,headers=header(first)),'Error',401)
        assert client.get('/api/auth/me',headers=header(second)).json()==second['user']
        assert client.get('/api/auth/me',headers=header(outsider)).json()==outsider['user']
        assert all(record.token_hash!=second['access_token'] for record in sessions._tokens.values())
        time[0]=1100  # inclusive expiry boundary, without sleeping
        for path,method in [('/api/auth/me','get'),('/api/auth/logout','post')]:
            assert_schema(getattr(client,method)(path,headers=header(second)),'Error',401)
        assert sessions.resolve(second['access_token']) is None
        # A new session uses the injected clock and remains usable.
        fresh=client.post('/api/auth/login',json={'email':'a@example.com','password':'password123'}).json()
        assert client.get('/api/auth/me',headers=header(fresh)).status_code==200


def test_me_and_logout_have_no_request_body_and_independent_sessions():
    app=create_app()
    paths=app.openapi()['paths']
    assert 'requestBody' not in paths['/api/auth/me']['get']
    assert 'requestBody' not in paths['/api/auth/logout']['post']
    first,second=MemorySessions(),MemorySessions()
    token=first.issue('opaque-user')
    assert first.resolve(token).user_id=='opaque-user'
    assert second.resolve(token) is None
