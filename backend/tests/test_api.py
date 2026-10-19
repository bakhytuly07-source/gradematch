import base64
from io import BytesIO
from pathlib import Path
from tempfile import SpooledTemporaryFile

import jsonschema
import numpy as np
from PIL import Image
import pytest
import yaml
from sqlalchemy import select

from app import models
from app.main import app

CONTRACT = yaml.safe_load((Path(__file__).resolve().parents[2] / "openapi.yaml").read_text())
SETTINGS = {"styleParams": {"id": "opaque", "shadowTint": [0.3, 0.6, 0.7],
            "highlightTint": [0.8, 0.5, 0.4], "baseSaturation": 1.1},
            "adjustments": {"intensity": 80, "contrast": 11, "saturation": -7, "warmth": 19}}


def assert_schema(response, schema, status=200):
    assert response.status_code == status, response.text
    jsonschema.validate(response.json(), {"$ref": f"#/components/schemas/{schema}", **CONTRACT})
    return response.json()


def register(client, email="user@example.com"):
    result = assert_schema(client.post("/api/auth/register", json={"email": email, "password": "password123"}), "AuthResult", 201)
    return {"Authorization": f"Bearer {result['access_token']}"}


def image_bytes(format="PNG", size=(300, 200)):
    buffer = BytesIO()
    Image.new("RGB", size, (180, 90, 55)).save(buffer, format=format)
    return buffer.getvalue()


def test_all_contract_operations_are_implemented():
    expected = {(path, method.upper(), operation["operationId"])
                for path, item in CONTRACT["paths"].items() for method, operation in item.items()
                if method != "parameters"}
    # Included routers may be lazy; inspect the generated public API rather
    # than relying on FastAPI's internal flat route representation.
    actual = {(path, method.upper(), operation["operationId"])
              for path, item in app.openapi()["paths"].items()
              for method, operation in item.items() if "operationId" in operation}
    assert expected == actual


def test_auth_validation_and_revocation(client, database):
    headers = register(client, "  USER@Example.com ")
    assert assert_schema(client.get("/api/auth/me", headers=headers), "User")["email"] == "user@example.com"
    assert_schema(client.post("/api/auth/register", json={"email": "user@example.com", "password": "password123"}), "Error", 409)
    for data in [{"email": "bad", "password": "password123"}, {"email": "a@b.co", "password": "short"}, {}]:
        assert_schema(client.post("/api/auth/register", json=data), "Error", 422)
    assert_schema(client.post("/api/auth/login", json={"email": "user@example.com", "password": "wrong"}), "Error", 401)
    login = assert_schema(client.post("/api/auth/login", json={"email": "USER@EXAMPLE.COM", "password": "password123"}), "AuthResult")
    with database() as db:
        user = db.scalar(select(models.User))
        assert "password123" not in user.password_hash
        tokens = db.scalars(select(models.AccessToken)).all()
        assert all(token.token_hash != login["access_token"] for token in tokens)
    response = client.post("/api/auth/logout", headers=headers)
    assert response.status_code == 204 and response.content == b""
    assert_schema(client.get("/api/auth/me", headers=headers), "Error", 401)
    valid = {"Authorization": f"Bearer {login['access_token']}"}
    assert client.get("/api/auth/me", headers=valid).status_code == 200
    with database() as db:
        token = db.scalar(select(models.AccessToken))
        token.expires_at = 0
        db.commit()
    assert_schema(client.get("/api/auth/me", headers=valid), "Error", 401)


def test_library_crud_ownership_thumbnail_and_persistence(client, database):
    owner = register(client)
    outsider = register(client, "other@example.com")
    thumb = "data:image/jpeg;base64," + base64.b64encode(image_bytes("JPEG", (256, 171))).decode()
    saved = assert_schema(client.post("/api/looks", headers=owner,
                          json={**SETTINGS, "name": "  My look  ", "thumbnail": thumb}), "Look", 201)
    assert saved["name"] == "My look" and not saved["is_favorite"]
    assert saved["created_at"] == saved["updated_at"] > 1_000_000_000_000
    data = base64.b64decode(saved["thumbnail_url"].split(",")[1])
    assert max(Image.open(BytesIO(data)).size) == 256
    path = "/api/looks/" + saved["id"]
    assert client.get("/api/looks", headers=outsider).json() == []
    for method, suffix, kwargs in [("get", "", {}), ("patch", "", {"json": {"name": "X"}}),
                                   ("delete", "", {}), ("post", "/favorite", {})]:
        assert_schema(getattr(client, method)(path + suffix, headers=outsider, **kwargs), "Error", 404)
    assert_schema(client.patch(path, headers=owner, json={"name": "  "}), "Error", 422)
    renamed = assert_schema(client.patch(path, headers=owner, json={"name": "  New  "}), "Look")
    assert renamed["name"] == "New" and renamed["updated_at"] > saved["updated_at"]
    assert assert_schema(client.post(path + "/favorite", headers=owner), "Look")["is_favorite"]
    assert not client.post(path + "/favorite", headers=owner).json()["is_favorite"]
    assert_schema(client.get(path, headers=owner), "Look")
    with database() as db:
        look = db.get(models.Look, saved["id"])
        assert look.name == "New" and look.style_params == SETTINGS["styleParams"]
    untitled = client.post("/api/looks", headers=owner, json={**SETTINGS, "name": " ", "thumbnail": ""}).json()
    assert untitled["name"] == "Untitled look" and untitled["thumbnail_url"] == ""
    assert client.get("/api/looks", headers=owner).json()[0]["id"] == untitled["id"]
    response = client.delete(path, headers=owner)
    assert response.status_code == 204 and not response.content
    assert_schema(client.get(path, headers=owner), "Error", 404)


@pytest.mark.parametrize("method,path", [("get", "/api/looks"), ("post", "/api/looks"),
    ("get", "/api/looks/opaque"), ("patch", "/api/looks/opaque"), ("delete", "/api/looks/opaque"),
    ("post", "/api/looks/opaque/favorite"), ("get", "/api/auth/me"), ("post", "/api/auth/logout")])
def test_protected_routes(client, method, path):
    assert_schema(getattr(client, method)(path), "Error", 401)


def test_render_export_exact_float32_and_identity(client):
    lut = assert_schema(client.post("/api/render-lut", json=SETTINGS), "LutData")
    cube = client.post("/api/download.cube", json=SETTINGS)
    assert cube.status_code == 200
    assert ".cube" in cube.headers["content-disposition"]
    rows = np.loadtxt(BytesIO(cube.content), skiprows=4, dtype=np.float32).ravel()
    np.testing.assert_array_equal(rows, np.array(lut["data"], dtype=np.float32))
    neutral = {**SETTINGS, "adjustments": {"intensity": 0, "contrast": 0, "saturation": 0, "warmth": 0}}
    values = np.array(client.post("/api/render-lut", json=neutral).json()["data"]).reshape(33, 33, 33, 3)
    np.testing.assert_array_equal(values[0, 0, :, 0], np.linspace(0, 1, 33))
    assert np.all(values[0, 0, :, 1:] == 0)
    invalid = {**SETTINGS, "adjustments": {**SETTINGS["adjustments"], "intensity": 101}}
    assert_schema(client.post("/api/render-lut", json=invalid), "Error", 422)


@pytest.mark.parametrize("format", ["PNG", "JPEG", "WEBP"])
def test_generate_guest_and_no_disk_spooling(client, database, monkeypatch, format):
    import starlette.formparsers
    files = []
    def track(*args, **kwargs):
        result = SpooledTemporaryFile(*args, **kwargs)
        files.append(result)
        return result
    monkeypatch.setattr(starlette.formparsers, "SpooledTemporaryFile", track)
    # Deliberately misleading MIME type: signature and decoded format take precedence.
    result = assert_schema(client.post("/api/generate", files={"referenceFile": ("image.bin", image_bytes(format), "application/octet-stream")}), "StyleParams")
    assert result["id"]
    assert files and all(not file._rolled and file.closed for file in files)
    with database() as db:
        assert db.scalar(select(models.Look)) is None
        assert db.scalar(select(models.User)) is None


def test_upload_limits_errors_and_cors(client):
    limit = 15 * 1024 * 1024
    jpeg = image_bytes("JPEG")
    exact = jpeg + b"\0" * (limit - len(jpeg))
    assert client.post("/api/generate", files={"referenceFile": ("large.jpg", exact)}).status_code == 200
    for data, status in [(exact + b"x", 413), (b"", 422), (b"not an image", 415), (b"\xff\xd8\xffbad", 422)]:
        assert_schema(client.post("/api/generate", files={"referenceFile": ("bad.jpg", data)}), "Error", status)
    assert_schema(client.post("/api/generate"), "Error", 422)
    assert_schema(client.post("/api/generate", content=b"bad", headers={"Content-Type": "multipart/form-data; boundary=x"}), "Error", 422)
    response = client.options("/api/looks", headers={"Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Authorization,Content-Type"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
