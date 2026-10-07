from fastapi.testclient import TestClient

from app.main import app


def test_analysis_access_reports_daily_allowance_and_tokens() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/analysis/access")
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload["tokens"], int)
        assert payload["tokens"] >= 0
        assert payload["free_remaining"] in (0, 1)
        assert len(payload["date"]) == 10


def test_same_match_analysis_unlock_is_idempotent() -> None:
    match_id = "analysis-access-idempotency-test"
    with TestClient(app) as client:
        first = client.post(f"/api/v1/analysis/{match_id}/unlock")
        assert first.status_code == 200
        first_payload = first.json()

        if not first_payload["unlocked"]:
            assert first_payload["free_remaining"] == 0
            assert first_payload["tokens"] == 0
            return

        second = client.post(f"/api/v1/analysis/{match_id}/unlock")
        assert second.status_code == 200
        second_payload = second.json()
        assert second_payload["unlocked"] is True
        assert second_payload["charged"] is False
        assert second_payload["source"] == first_payload["source"]
        assert second_payload["tokens"] == first_payload["tokens"]
