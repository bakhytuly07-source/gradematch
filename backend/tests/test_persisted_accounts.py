from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import create_app
from app.models import User


def test_restart_and_concurrent_duplicate(database, monkeypatch):
    url = str(database.kw['bind'].url)
    def new_app():
        return create_app(storage='orm', database_url=url)
    app = new_app()
    with TestClient(app) as client:
        result = client.post('/api/auth/register', json={'email': ' USER@Example.com ', 'password': 'password123'})
        assert result.status_code == 201
        user = result.json()['user']
    app.state.engine.dispose()
    app = new_app()
    with TestClient(app) as client:
        result = client.post('/api/auth/login', json={'email': 'User@EXAMPLE.com', 'password': 'password123'})
        assert result.status_code == 200 and result.json()['user'] == user
        wrong = client.post('/api/auth/login', json={'email': 'user@example.com', 'password': 'bad'})
        missing = client.post('/api/auth/login', json={'email': 'unknown@example.com', 'password': 'bad'})
        assert wrong.status_code == missing.status_code == 401 and wrong.json() == missing.json()
        def register(email):
            return client.post('/api/auth/register', json={'email': email, 'password': 'password123'})
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(register, [' DUP@Example.com ', 'dup@example.com']))
        assert sorted(r.status_code for r in results) == [201, 409]
        assert register('next@example.com').status_code == 201
    with database() as db:
        assert len(list(db.scalars(select(User).where(User.email == 'dup@example.com')))) == 1
    app.state.engine.dispose()
