import base64
from copy import deepcopy
from io import BytesIO

import numpy as np
from PIL import Image
import pytest

from app.color import build_lut
from app.looks import MemoryLooks
from app.schemas import SaveLookInput
from test_api import SETTINGS, assert_schema, image_bytes, register


def thumb(format='JPEG',size=(256,170)):
    return 'data:image/jpeg;base64,'+base64.b64encode(image_bytes(format,size)).decode()


def test_save_private_complete_metadata_and_no_originals(memory_client,memory_app):
    owner=register(memory_client)
    other=register(memory_client,'other@example.com')
    body={**deepcopy(SETTINGS),'name':'  Test  ','thumbnail':thumb()}
    saved=assert_schema(memory_client.post('/api/looks',headers=owner,json=body),'Look',201)
    assert saved['id'] and saved['name']=='Test' and not saved['is_favorite']
    assert saved['created_at']==saved['updated_at']>1_000_000_000_000
    assert saved['style_params']==SETTINGS['styleParams'] and saved['adjustments']==SETTINGS['adjustments']
    with Image.open(BytesIO(base64.b64decode(saved['thumbnail_url'].split(',')[1]))) as image:
        assert image.format=='JPEG' and max(image.size)==256 and not image.getexif()
    assert memory_client.get('/api/looks',headers=other).json()==[]
    assert_schema(memory_client.get('/api/looks/'+saved['id'],headers=other),'Error',404)
    assert len(memory_app.state.memory.looks._records)==1
    assert 'owner' not in saved and 'user_id' not in saved
    unnamed=assert_schema(memory_client.post('/api/looks',headers=owner,json={**SETTINGS,'name':'  ','thumbnail':''}),'Look',201)
    assert unnamed['name']=='Untitled look' and unnamed['thumbnail_url']==''


@pytest.mark.parametrize('thumbnail',[thumb(size=(255,170)),thumb(size=(257,170)),thumb('PNG'),
    'data:image/jpeg;base64,???','data:image/png;base64,AAAA','https://example.com/photo.jpg'])
def test_invalid_thumbnail_creates_no_partial_record(memory_client,memory_app,thumbnail):
    headers=register(memory_client)
    response=memory_client.post('/api/looks',headers=headers,json={**SETTINGS,'name':'x','thumbnail':thumbnail})
    assert assert_schema(response,'Error',422)['code']=='validation'
    assert not memory_app.state.memory.looks._records


def test_save_settings_and_auth_errors_create_no_records(memory_client,memory_app):
    body={**deepcopy(SETTINGS),'name':'x','thumbnail':''}
    for headers in [{},{'Authorization':'Bearer missing'}]:
        assert_schema(memory_client.post('/api/looks',headers=headers,json=body),'Error',401)
    owner=register(memory_client)
    body['adjustments']['warmth']=51
    assert_schema(memory_client.post('/api/looks',headers=owner,json=body),'Error',422)
    assert not memory_app.state.memory.looks._records


def test_repository_deep_isolation_and_saved_settings_reproduce_lut():
    first,second=MemoryLooks(),MemoryLooks()
    body=SaveLookInput.model_validate({**deepcopy(SETTINGS),'name':'x','thumbnail':''})
    saved=first.create('owner',body)
    expected=build_lut(SETTINGS)
    body.style_params.shadow_tint[0]=.99
    saved.adjustments.warmth=-50
    loaded=first.get('owner',saved.id)
    np.testing.assert_array_equal(build_lut({'styleParams':loaded.style_params,'adjustments':loaded.adjustments}),expected)
    loaded.style_params.highlight_tint[0]=.01
    assert first.get('owner',saved.id).style_params.highlight_tint[0]==.8
    assert second.for_owner('owner')==[]
