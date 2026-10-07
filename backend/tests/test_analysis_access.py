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


def test_rich_analysis_uses_server_fixture_and_model_context(monkeypatch) -> None:
    from app.api import analysis as analysis_api

    monkeypatch.setattr(analysis_api.settings, "openrouter_api_key", "test-key")

    async def fixture(db, user, match_id):
        return {
            "id": match_id,
            "home_team": {"id": "10", "name": "Server Home"},
            "away_team": {"id": "20", "name": "Server Away"},
            "competition": {"name": "Server League"},
        }

    class Provider:
        async def get_recent_results(self, team_id, limit=5):
            return []

    async def model(match_id, home_name=None, away_name=None, competition=None):
        assert home_name == "Server Home"
        assert away_name == "Server Away"
        assert competition == "Server League"
        return {"available": True, "pick": "HOME", "probabilities": {"HOME": 0.5, "DRAW": 0.3, "AWAY": 0.2}}

    captured = {}
    async def explain(**kwargs):
        captured.update(kwargs)
        return "Server-grounded explanation"

    monkeypatch.setattr(analysis_api, "_find_personalized_match", fixture)
    monkeypatch.setattr(analysis_api, "get_football_provider", lambda: Provider())
    monkeypatch.setattr(analysis_api, "predict_match", model)
    monkeypatch.setattr(analysis_api, "explain_match", explain)

    with TestClient(app) as client:
        response = client.post("/api/v1/analysis/server-grounding-test/rich")
        assert response.status_code == 200
        assert captured["home_team"] == "Server Home"
        assert captured["away_team"] == "Server Away"
        assert captured["model_outlook"]["pick"] == "HOME"
