from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from app.users import MemoryUsers
from test_api import SETTINGS, assert_schema


def test_registration_and_issued_token_use_injected_memory_repository(caplog,monkeypatch):
    import app.database as database
    def no_database(*args,**kwargs):
        raise AssertionError('memory API must not open database sessions')
    monkeypatch.setattr(database,'SessionLocal',no_database)
    users=MemoryUsers()
    application=create_app(users=users)
    with TestClient(application) as client:
        result=assert_schema(client.post('/api/auth/register',json={'email':'  USER@Example.com ','password':'password-secret'}),'AuthResult',201)
        assert result['token_type']=='bearer' and result['access_token']
        assert result['user']['email']=='user@example.com'
        headers={'Authorization':'Bearer '+result['access_token']}
        assert client.get('/api/auth/me',headers=headers).json()==result['user']
        assert users.find('user@example.com').id==result['user']['id']
        assert client.post('/api/render-lut',json=SETTINGS).status_code==200
        duplicate=client.post('/api/auth/register',json={'email':'USER@EXAMPLE.COM','password':'different-password'})
        assert_schema(duplicate,'Error',409)
        assert users.authenticate('user@example.com','password-secret') is not None
        assert 'password-secret' not in result.__repr__()+caplog.text
        assert users.find('user@example.com').password_hash not in str(result)+caplog.text
    with TestClient(create_app()) as isolated:
        assert isolated.get('/api/auth/me',headers=headers).status_code==401


@pytest.mark.parametrize('body',[{}, {'email':'bad','password':'password'},
    {'email':'a@b.co','password':'short'}, {'email':True,'password':'password'},
    {'email':'a@b.co','password':12345678}, {'email':'a@b.co'}])
def test_invalid_registration_has_no_partial_account(memory_client,memory_app,body,caplog):
    response=memory_client.post('/api/auth/register',json=body)
    assert assert_schema(response,'Error',422)['code']=='validation'
    assert not memory_app.state.memory.users._by_id
    assert 'password' not in response.text.lower()+caplog.text.lower()
