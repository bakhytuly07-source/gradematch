from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.looks import MemoryLooks
from app.main import create_app
from app.schemas import SaveLookInput
from test_api import SETTINGS, assert_schema, register


def test_empty_isolated_ordered_complete_lists_with_timestamp_ties():
    time=[1000_000_000_000]
    repo=MemoryLooks(clock=lambda:time[0])
    app=create_app(looks=repo)
    with TestClient(app) as client:
        owner=register(client)
        other=register(client,'other@example.com')
        assert client.get('/api/looks',headers=owner).json()==[]
        def save(headers,name):
            return assert_schema(client.post('/api/looks',headers=headers,json={**SETTINGS,'name':name,'thumbnail':''}),'Look',201)
        first=save(owner,'first')
        tied=save(owner,'tie')
        save(other,'private')
        time[0]+=1
        newest=save(owner,'newest')
        expected=[newest,*sorted([first,tied],key=lambda value:value['id'],reverse=True)]
        for _ in range(3):
            response=client.get('/api/looks',headers=owner)
            assert response.status_code==200 and response.json()==expected
            for look in response.json():
                assert set(look)=={'id','name','style_params','adjustments','thumbnail_url','is_favorite','created_at','updated_at'}
                assert 'private' not in look['name']
        assert [value['name'] for value in client.get('/api/looks',headers=other).json()]==['private']
        save(other,'second private')
        assert client.get('/api/looks',headers=owner).json()==expected
        assert_schema(client.get('/api/looks'),'Error',401)
        assert_schema(client.get('/api/looks',headers={'Authorization':'Bearer wrong'}),'Error',401)
    operation=app.openapi()['paths']['/api/looks']['get']
    assert 'requestBody' not in operation and not operation.get('parameters')


def test_returned_lists_cannot_mutate_repository_and_favorites_are_atomic():
    repo=MemoryLooks(clock=lambda:1000)
    saved=repo.create('owner',SaveLookInput.model_validate({**SETTINGS,'name':'a','thumbnail':''}))
    rows=repo.for_owner('owner')
    rows[0].style_params.shadow_tint[0]=1
    rows.clear()
    assert repo.get('owner',saved.id).style_params.shadow_tint[0]==.3
    # The list snapshots remain consistent alongside existing favorite operations.
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _:repo.toggle_favorite('owner',saved.id),range(20)))
    final=repo.for_owner('owner')[0]
    assert final.is_favorite is False
    assert final.created_at==1000 and final.updated_at==1020
