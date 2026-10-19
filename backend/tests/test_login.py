import pytest

from test_api import assert_schema


def test_login_normalization_tokens_and_generic_errors(memory_client,memory_app,caplog):
    created=assert_schema(memory_client.post('/api/auth/register',json={'email':'user@example.com','password':'password-secret'}),'AuthResult',201)
    result=assert_schema(memory_client.post('/api/auth/login',json={'email':' USER@EXAMPLE.COM ','password':'password-secret'}),'AuthResult')
    assert result['user']==created['user']
    assert result['access_token']!=created['access_token'] and result['token_type']=='bearer'
    headers={'Authorization':'Bearer '+result['access_token']}
    assert memory_client.get('/api/auth/me',headers=headers).json()==created['user']
    wrong=memory_client.post('/api/auth/login',json={'email':'user@example.com','password':'wrong-secret'})
    unknown=memory_client.post('/api/auth/login',json={'email':'unknown@example.com','password':'wrong-secret'})
    assert_schema(wrong,'Error',401)
    assert wrong.json()==unknown.json()=={'code':'auth','message':'Email or password is incorrect.'}
    assert len(memory_app.state.memory.sessions._tokens)==2
    for secret in ['password-secret','wrong-secret',memory_app.state.memory.users.find('user@example.com').password_hash]:
        assert secret not in caplog.text+str(result)+wrong.text+unknown.text


@pytest.mark.parametrize('body',[{}, {'email':'user@example.com'}, {'password':'password-secret'},
    {'email':123,'password':'password-secret'}, {'email':'a@b.co','password':None}])
def test_missing_or_malformed_login(memory_client,memory_app,body):
    assert assert_schema(memory_client.post('/api/auth/login',json=body),'Error',422)['code']=='validation'
    assert not memory_app.state.memory.sessions._tokens


def test_login_input_does_not_invent_registration_constraints(memory_client):
    # LoginInput in the contract has no email pattern/minimum password length.
    response=memory_client.post('/api/auth/login',json={'email':'unknown','password':''})
    assert assert_schema(response,'Error',401)['code']=='auth'
