from fastapi.testclient import TestClient

from app.main import app


def test_application_lifecycle():
    with TestClient(app) as client:
        assert client.get("/openapi.json").status_code == 200
