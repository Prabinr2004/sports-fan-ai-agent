from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def _register(client, name="Fan"):
    email = f"fan-{uuid4().hex}@example.com"
    response = client.post("/api/v1/auth/register", json={
        "email": email, "display_name": name, "password": "secure-test-password-2026",
    })
    assert response.status_code == 201, response.text
    return email


def test_registration_login_logout_and_protected_profile():
    with TestClient(app) as client:
        assert client.get("/api/v1/profile").status_code == 401
        email = _register(client)
        assert client.get("/api/v1/auth/me").json()["user"]["email"] == email
        assert client.get("/api/v1/profile").status_code == 200
        assert client.post("/api/v1/auth/logout").status_code == 200
        assert client.get("/api/v1/profile").status_code == 401
        assert client.post("/api/v1/auth/login", json={
            "email": email, "password": "secure-test-password-2026",
        }).status_code == 200
        assert client.get("/api/v1/profile").status_code == 200


def test_accounts_have_separate_profiles():
    with TestClient(app) as first, TestClient(app) as second:
        _register(first, "First Fan")
        _register(second, "Second Fan")
        a = first.get("/api/v1/profile").json()
        b = second.get("/api/v1/profile").json()
        assert a["id"] != b["id"]
        assert a["display_name"] == "First Fan"
        assert b["display_name"] == "Second Fan"


def test_registration_rejects_short_password():
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/register", json={
            "email": f"fan-{uuid4().hex}@example.com",
            "display_name": "Fan",
            "password": "short",
        })
        assert response.status_code == 422
