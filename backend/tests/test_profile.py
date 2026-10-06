from fastapi.testclient import TestClient

from app.main import app


def test_local_profile_is_available() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/profile")
        assert response.status_code == 200
        payload = response.json()
        assert payload["display_name"] == "Prabin"
        assert payload["mode"] == "local-development"
        assert isinstance(payload["favorites"], list)
