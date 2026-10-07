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


def test_profile_achievements_are_progress_backed() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/profile/achievements")
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 7
        assert 0 <= payload["unlocked"] <= payload["total"]
        assert {"quiz_completions", "predictions", "scored_predictions", "correct_predictions"} <= payload["stats"].keys()
        assert all(item["target"] > 0 for item in payload["achievements"])
        assert all(0 <= item["progress"] <= item["target"] for item in payload["achievements"])
