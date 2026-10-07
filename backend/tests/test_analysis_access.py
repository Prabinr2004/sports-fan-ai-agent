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


def test_rich_analysis_requires_server_match_when_ai_is_configured(monkeypatch) -> None:
    from app.api import analysis as analysis_api

    monkeypatch.setattr(analysis_api.settings, "openrouter_api_key", "test-key")
    async def missing_match(db, user, match_id):
        return None
    monkeypatch.setattr(analysis_api, "_find_personalized_match", missing_match)

    with TestClient(app) as client:
        response = client.post("/api/v1/analysis/not-a-real-personalized-match/rich")
        assert response.status_code == 404
        assert "personalized match feed" in response.json()["detail"]
