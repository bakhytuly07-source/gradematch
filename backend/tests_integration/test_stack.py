"""HTTP scenarios against real services; no in-process clients or shared users."""
import time
from uuid import uuid4

import httpx
import jsonschema
import numpy as np
import pytest
import yaml

from conftest import ROOT, compose

ADJUSTMENTS = {"intensity": 73, "contrast": 12, "saturation": -8, "warmth": 9}
STYLE = {"id": "integration", "shadowTint": [0.1, 0.2, 0.3],
         "highlightTint": [0.8, 0.7, 0.6], "baseSaturation": 1.1}


def checked(response, status=200):
    assert response.status_code == status, response.text
    return response.json() if response.content else None


def register(api):
    credentials = {"email": f"integration-{uuid4().hex}@example.com", "password": "Integration93!"}
    account = checked(api.post("/api/auth/register", json=credentials), 201)
    return credentials, account


def bearer(account):
    return {"Authorization": f"Bearer {account['access_token']}"}


@pytest.fixture
def account(api):
    _, result = register(api)
    yield result
    api.post("/api/auth/logout", headers=bearer(result))


@pytest.fixture
def saved_look(api, account):
    payload = {"name": "Integration persistence", "thumbnail": "",
               "styleParams": STYLE, "adjustments": ADJUSTMENTS}
    look = checked(api.post("/api/looks", json=payload, headers=bearer(account)), 201)
    yield look
    response = api.delete(f"/api/looks/{look['id']}", headers=bearer(account))
    assert response.status_code in (204, 404), response.text


def test_services(api, frontend):
    checked_docs = api.get("/docs")
    assert checked_docs.status_code == 200
    assert frontend.get("/").status_code == 200
    assert frontend.get("/login").status_code == 200


def test_registration_reaches_postgres(api, account):
    # Use credentials inside the db container, including Compose/.env overrides.
    # psql variable quoting prevents the email from becoming SQL syntax.
    output = compose(
        "exec", "-T", "db", "sh", "-c",
        'psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -v ON_ERROR_STOP=1 '
        '-v "email=$1" -f - <<\'SQL\'\nSELECT email FROM users WHERE email = :\'email\';\nSQL',
        "sh", account["user"]["email"],
    )
    assert output.strip() == account["user"]["email"]


def test_guest_generate_render_and_cube_exact_parity(api):
    reference = (ROOT / "backend/evaluation/reference-neutral.jpg").read_bytes()
    style = checked(api.post("/api/generate", files={"referenceFile": ("neutral.jpg", reference, "image/jpeg")}))
    contract = yaml.safe_load((ROOT / "openapi.yaml").read_text())
    jsonschema.validate(style, contract["components"]["schemas"]["StyleParams"])
    settings = {"styleParams": style, "adjustments": ADJUSTMENTS}
    lut = checked(api.post("/api/render-lut", json=settings))
    assert lut["size"] == 33
    assert len(lut["data"]) == 107811
    assert all(type(value) in (int, float) for value in lut["data"])
    response = api.post("/api/download.cube", json=settings)
    assert response.status_code == 200, response.text
    rows = []
    for line in response.text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith(("TITLE", "LUT_3D_SIZE", "DOMAIN_MIN", "DOMAIN_MAX")):
            continue
        row = line.split()
        assert len(row) == 3, line
        rows.append([float(value) for value in row])
    assert len(rows) == 35937
    np.testing.assert_array_equal(np.asarray(rows, dtype=np.float32).ravel(),
                                  np.asarray(lut["data"], dtype=np.float32))


@pytest.mark.parametrize("filename,payload,mime,status", [
    ("unsupported.gif", b"GIF89a" + b"\x00" * 30, "image/gif", 415),
    ("corrupt.jpg", b"\xff\xd8\xffcorrupt", "image/jpeg", 422),
    ("large.jpg", b"\xff\xd8\xff" + b"\x00" * (15 * 1024 * 1024 - 2), "image/jpeg", 413),
], ids=["unsupported", "corrupt", "one-byte-over-limit"])
def test_generate_rejects_invalid_upload(api, filename, payload, mime, status):
    response = api.post("/api/generate", files={"referenceFile": (filename, payload, mime)})
    assert response.status_code == status, response.text


def test_account_login_me_logout(api):
    credentials, registered = register(api)
    try:
        logged_in = checked(api.post("/api/auth/login", json=credentials))
        headers = bearer(logged_in)
        try:
            assert checked(api.get("/api/auth/me", headers=headers)) == registered["user"]
            checked(api.post("/api/auth/logout", headers=headers), 204)
            assert api.get("/api/auth/me", headers=headers).status_code == 401
        finally:
            api.post("/api/auth/logout", headers=headers)
    finally:
        api.post("/api/auth/logout", headers=bearer(registered))


def test_library_crud_and_owner_isolation(api, account, saved_look):
    headers = bearer(account)
    path = f"/api/looks/{saved_look['id']}"
    assert saved_look in checked(api.get("/api/looks", headers=headers))
    _, second = register(api)
    try:
        assert api.get(path, headers=bearer(second)).status_code == 404
        assert checked(api.get(path, headers=headers)) == saved_look
    finally:
        checked(api.post("/api/auth/logout", headers=bearer(second)), 204)
    checked(api.patch(path, json={"name": "Renamed integration look"}, headers=headers))
    assert checked(api.get(path, headers=headers))["name"] == "Renamed integration look"
    assert saved_look["is_favorite"] is False
    checked(api.post(path + "/favorite", headers=headers))
    persisted = checked(api.get(path, headers=headers))
    assert persisted["is_favorite"] is True
    assert persisted in checked(api.get("/api/looks", headers=headers))
    checked(api.delete(path, headers=headers), 204)
    assert all(look["id"] != saved_look["id"] for look in checked(api.get("/api/looks", headers=headers)))
    assert api.get(path, headers=headers).status_code == 404


def test_cors_preflights(api):
    for origin, allowed in [("http://localhost:3000", True), ("http://evil.example", False)]:
        response = api.options("/api/generate", headers={
            "Origin": origin, "Access-Control-Request-Method": "POST"})
        if allowed:
            assert response.is_success, response.text
            assert response.headers.get("access-control-allow-origin") == origin
        else:
            assert response.headers.get("access-control-allow-origin") != origin


def test_persistence_after_backend_restart(api, account, saved_look):
    headers = bearer(account)  # The exact same token must survive the restart.
    compose("restart", "backend", timeout=60)
    deadline = time.monotonic() + 90
    diagnostic = "No health response"
    while time.monotonic() < deadline:
        health = compose("ps", "--format", "{{.Health}}", "backend", timeout=5).strip()
        diagnostic = f"Compose backend health: {health!r}"
        if health == "healthy":
            try:
                response = api.get("/docs", timeout=2)
                diagnostic += f"; /docs HTTP {response.status_code}"
                if response.status_code == 200:
                    break
            except httpx.HTTPError as exc:
                diagnostic += f"; {exc}"
        time.sleep(0.5)
    else:
        pytest.fail(f"Backend did not become healthy within 90 seconds after restart: {diagnostic}")
    looks = checked(api.get("/api/looks", headers=headers))
    assert next((look for look in looks if look["id"] == saved_look["id"]), None) == saved_look
