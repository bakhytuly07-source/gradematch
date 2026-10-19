from copy import deepcopy
import json

import numpy as np
import pytest

from app.color import build_lut
from test_api import SETTINGS, assert_schema


def test_guest_render_matches_builder_and_grid_order(client):
    first=assert_schema(client.post('/api/render-lut',json=SETTINGS),'LutData')
    second=client.post('/api/render-lut',json=SETTINGS).json()
    assert first==second
    samples=np.array(first['data'],dtype=np.float32).reshape(-1,3)
    np.testing.assert_array_equal(samples,build_lut(SETTINGS))
    assert len(first['data'])==107811 and first['size']==33
    identity=deepcopy(SETTINGS)
    identity['adjustments']={'intensity':0,'contrast':0,'saturation':0,'warmth':0}
    grid=np.array(client.post('/api/render-lut',json=identity).json()['data']).reshape(33,33,33,3)
    for b,g,r in [(1,3,17),(32,0,8),(9,21,31)]:
        np.testing.assert_array_equal(grid[b,g,r],[r/32,g/32,b/32])


INVALID=[{}, {'styleParams':{}}, {'adjustments':{}}, None]
for path,value in [('shadowTint',[.5,.5]),('highlightTint',[.5,.5,.5,.5]),('shadowTint',[-.1,.5,.5]),
                   ('highlightTint',[True,.5,.5]),('baseSaturation','1'),('baseSaturation',float('nan')),
                   ('baseSaturation',float('inf'))]:
    item=deepcopy(SETTINGS)
    item['styleParams'][path]=value
    INVALID.append(item)
for field,value in [('intensity',-1),('warmth',51),('saturation','0'),('contrast',None)]:
    item=deepcopy(SETTINGS)
    item['adjustments'][field]=value
    INVALID.append(item)


@pytest.mark.parametrize('body',INVALID)
def test_invalid_settings_have_safe_shared_errors(client,body):
    # Raw JSON exercises NaN/Infinity rejection beyond HTTPX's strict encoder.
    response=client.post('/api/render-lut',content=json.dumps(body),headers={'Content-Type':'application/json'})
    result=assert_schema(response,'Error',422)
    assert result['code']=='validation'
    assert set(result)=={'code','message'}


def test_unexpected_render_error_is_generic_and_does_not_log_payload(client,monkeypatch,caplog):
    import app.main as module
    def fail(settings):
        raise RuntimeError('secret-input-must-not-be-logged')
    monkeypatch.setattr(module,'build_lut',fail)
    response=client.post('/api/render-lut',json=SETTINGS)
    error=assert_schema(response,'Error',500)
    assert error=={'code':'unknown','message':'Unexpected processing or server failure.'}
    assert 'secret-input-must-not-be-logged' not in caplog.text+response.text
