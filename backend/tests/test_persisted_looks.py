import base64
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import create_app
from app.models import Look
from test_api import SETTINGS, image_bytes, register


def test_reconnected_private_lists_and_failure(database):
    url = str(database.kw['bind'].url)
    thumb = 'data:image/jpeg;base64,' + base64.b64encode(image_bytes('JPEG', (256, 171))).decode()
    saved = []
    for restart in range(2):
        app = create_app(storage='orm', database_url=url)
        with TestClient(app, raise_server_exceptions=False) as client:
            for i in range(2):
                email = f'{i}@example.com'
                if not restart:
                    headers = register(client, email)
                    assert client.get('/api/looks', headers=headers).json() == []
                    response = client.post('/api/looks', headers=headers,
                        json={**SETTINGS, 'name': ' Same ', 'thumbnail': thumb})
                    assert response.status_code == 201
                    saved.append(response.json())
                    assert client.post('/api/looks', headers=headers,
                        json={**SETTINGS, 'name': 'Bad', 'thumbnail': 'original'}).status_code == 422
                else:
                    auth = client.post('/api/auth/login', json={'email': email, 'password': 'password123'}).json()
                    headers = {'Authorization': 'Bearer ' + auth['access_token']}
                assert client.get('/api/looks', headers=headers).json() == [saved[i]]
                assert 'user_id' not in saved[i]
        app.state.engine.dispose()
    with database() as db:
        assert len(list(db.scalars(select(Look)))) == 2
