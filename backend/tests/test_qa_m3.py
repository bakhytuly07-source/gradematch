from copy import deepcopy
from io import BytesIO

import numpy as np
import pytest

from test_api import SETTINGS, assert_schema, image_bytes


@pytest.mark.parametrize('format', ['JPEG', 'PNG', 'WEBP'])
def test_memory_guest_color_operations_without_database(memory_client, memory_app, monkeypatch, format):
    import app.database as database
    def forbidden(*args, **kwargs):
        raise AssertionError('guest memory operation opened database')
    monkeypatch.setattr(database, 'SessionLocal', forbidden)
    style = assert_schema(memory_client.post('/api/generate', files={
        'referenceFile': ('misleading.txt', image_bytes(format), 'text/plain')}), 'StyleParams')
    body = {**deepcopy(SETTINGS), 'styleParams': style}
    rendered = assert_schema(memory_client.post('/api/render-lut', json=body), 'LutData')
    exported = memory_client.post('/api/download.cube', json=body)
    assert exported.status_code == 200
    np.testing.assert_array_equal(
        np.loadtxt(BytesIO(exported.content), skiprows=4, dtype=np.float32).ravel(),
        np.array(rendered['data'], dtype=np.float32))
    state = memory_app.state.memory
    assert not state.users._by_id and not state.sessions._tokens and not state.looks._records


@pytest.mark.parametrize('field,value', [
    ('intensity', -1), ('intensity', 101), ('contrast', -51), ('contrast', 51),
    ('saturation', -51), ('saturation', 51), ('warmth', -51), ('warmth', 51)])
@pytest.mark.parametrize('path', ['/api/render-lut', '/api/download.cube'])
def test_all_control_range_errors_in_memory(memory_client, field, value, path):
    body = deepcopy(SETTINGS)
    body['adjustments'][field] = value
    assert assert_schema(memory_client.post(path, json=body), 'Error', 422)['code'] == 'validation'


def test_eight_character_password_registration_boundary(memory_client):
    result = assert_schema(memory_client.post('/api/auth/register', json={
        'email': 'boundary@example.com', 'password': '12345678'}), 'AuthResult', 201)
    assert memory_client.get('/api/auth/me', headers={
        'Authorization': 'Bearer ' + result['access_token']}).json() == result['user']
