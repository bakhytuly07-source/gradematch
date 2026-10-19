from copy import deepcopy
from io import BytesIO

import numpy as np
import pytest

from test_api import SETTINGS, assert_schema


@pytest.mark.parametrize('adjustments', [
    {'intensity':0,'contrast':0,'saturation':0,'warmth':0},
    {'intensity':80,'contrast':0,'saturation':0,'warmth':0},
    {'intensity':100,'contrast':50,'saturation':-50,'warmth':50},
    {'intensity':0,'contrast':-50,'saturation':50,'warmth':-50},
])
def test_guest_download_matches_render_exactly(client,adjustments,monkeypatch):
    import app.main as module
    real=module.build_lut
    calls=[]
    def track(settings):
        calls.append(settings.model_dump(by_alias=True))
        return real(settings)
    monkeypatch.setattr(module,'build_lut',track)
    body=deepcopy(SETTINGS)
    body['adjustments']=adjustments
    rendered=client.post('/api/render-lut',json=body).json()
    response=client.post('/api/download.cube',json=body)
    assert response.status_code==200
    assert response.headers['content-type'].startswith('text/plain')
    assert response.headers['content-disposition']=='attachment; filename="gradematch-look.cube"'
    assert len(response.text.splitlines())==35941
    samples=np.loadtxt(BytesIO(response.content),skiprows=4,dtype=np.float32).ravel()
    np.testing.assert_array_equal(samples,np.array(rendered['data'],dtype=np.float32))
    assert calls==[body,body]


@pytest.mark.parametrize('body',[{}, {'styleParams':{},'adjustments':{}}, {'id':'saved-look-is-not-settings'}])
def test_missing_or_invalid_settings(client,body):
    assert assert_schema(client.post('/api/download.cube',json=body),'Error',422)['code']=='validation'


def test_unexpected_export_failure(client,monkeypatch):
    import app.main as module
    def fail(data):
        raise RuntimeError('internal writer failure')
    monkeypatch.setattr(module,'write_cube',fail)
    error=assert_schema(client.post('/api/download.cube',json=SETTINGS),'Error',500)
    assert error['code']=='unknown' and 'internal writer failure' not in error['message']
