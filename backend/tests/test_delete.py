from copy import deepcopy
from io import BytesIO
from tempfile import SpooledTemporaryFile

import numpy as np
import pytest

from test_api import SETTINGS, assert_schema, image_bytes, register
from test_save import thumb


def save(client,headers,name='saved'):
    return assert_schema(client.post('/api/looks',headers=headers,json={**SETTINGS,'name':name,'thumbnail':thumb()}),'Look',201)


def test_delete_only_owned_record_and_remove_all_retained_data(memory_client,memory_app):
    owner=register(memory_client)
    other=register(memory_client,'other@example.com')
    saved=save(memory_client,owner)
    keep=save(memory_client,owner,'keep')
    foreign=save(memory_client,other,'foreign')
    path='/api/looks/'+saved['id']
    missing=memory_client.delete('/api/looks/not-a-uuid',headers=owner)
    denied=memory_client.delete('/api/looks/'+foreign['id'],headers=owner)
    assert_schema(missing,'Error',404)
    assert denied.json()==missing.json()
    for headers in [{},{'Authorization':'Bearer invalid'}]:
        assert_schema(memory_client.delete(path,headers=headers),'Error',401)
    assert len(memory_app.state.memory.looks._records)==3
    response=memory_client.delete(path,headers=owner)
    assert response.status_code==204 and response.content==b''
    assert saved['id'] not in memory_app.state.memory.looks._records
    assert_schema(memory_client.get(path,headers=owner),'Error',404)
    assert_schema(memory_client.delete(path,headers=owner),'Error',404)
    assert memory_client.get('/api/looks',headers=owner).json()==[keep]
    assert memory_client.get('/api/looks',headers=other).json()==[foreign]
    assert memory_client.get('/api/looks/'+foreign['id'],headers=other).json()==foreign


def test_empty_library_and_opaque_ids(memory_client,memory_app):
    headers=register(memory_client)
    assert_schema(memory_client.delete('/api/looks/opaque-key-not-a-uuid',headers=headers),'Error',404)
    assert not memory_app.state.memory.looks._records
    assert memory_client.get('/api/looks',headers=headers).json()==[]


def test_complete_memory_api_journey_without_database_or_uploaded_original_storage(memory_client,memory_app,monkeypatch):
    import app.database as database
    import starlette.formparsers
    def forbid_database(*args,**kwargs):
        raise AssertionError('in-memory API opened a database')
    monkeypatch.setattr(database,'SessionLocal',forbid_database)
    files=[]
    def track(*args,**kwargs):
        file=SpooledTemporaryFile(*args,**kwargs)
        files.append(file)
        return file
    monkeypatch.setattr(starlette.formparsers,'SpooledTemporaryFile',track)
    generated=assert_schema(memory_client.post('/api/generate',files={'referenceFile':('x.png',image_bytes())}),'StyleParams')
    state=memory_app.state.memory
    assert not state.users._by_id and not state.looks._records and not state.sessions._tokens
    assert files and all(file.closed and not file._rolled for file in files)
    assert_schema(memory_client.post('/api/generate',files={'referenceFile':('bad.png',b'\x89PNG\r\n\x1a\ncorrupt')}),'Error',422)
    assert all(file.closed and not file._rolled for file in files)
    owner=register(memory_client)
    other=register(memory_client,'other@example.com')
    login=assert_schema(memory_client.post('/api/auth/login',json={'email':'USER@EXAMPLE.COM','password':'password123'}),'AuthResult')
    login_header={'Authorization':'Bearer '+login['access_token']}
    assert memory_client.get('/api/auth/me',headers=login_header).json()==login['user']
    settings={**deepcopy(SETTINGS),'styleParams':generated}
    saved=assert_schema(memory_client.post('/api/looks',headers=owner,json={**settings,'name':'all routes','thumbnail':''}),'Look',201)
    path='/api/looks/'+saved['id']
    assert memory_client.get('/api/looks',headers=owner).json()==[saved]
    assert memory_client.get(path,headers=owner).json()==saved
    for method,suffix,kwargs in [('get','',{}),('patch','',{'json':{'name':'intrusion'}}),('post','/favorite',{}),('delete','',{})]:
        assert_schema(getattr(memory_client,method)(path+suffix,headers=other,**kwargs),'Error',404)
    renamed=assert_schema(memory_client.patch(path,headers=owner,json={'name':'  Renamed  '}),'Look')
    assert renamed['name']=='Renamed' and renamed['updated_at']>saved['updated_at']
    favorite=assert_schema(memory_client.post(path+'/favorite',headers=owner),'Look')
    assert favorite['is_favorite'] and favorite['style_params']==generated
    rendered=assert_schema(memory_client.post('/api/render-lut',json=settings),'LutData')
    cube=memory_client.post('/api/download.cube',json=settings)
    assert cube.status_code==200
    np.testing.assert_array_equal(np.loadtxt(BytesIO(cube.content),skiprows=4,dtype=np.float32).ravel(),
                                  np.array(rendered['data'],dtype=np.float32))
    assert memory_client.delete(path,headers=owner).status_code==204
    assert not state.looks._records
    assert memory_client.get('/api/looks',headers=owner).json()==[]
    assert memory_client.post('/api/auth/logout',headers=owner).status_code==204
    assert memory_client.get('/api/auth/me',headers=owner).status_code==401
    assert memory_client.get('/api/auth/me',headers=login_header).status_code==200
