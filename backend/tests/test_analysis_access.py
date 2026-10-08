from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def sign_in(client):
    result = client.post('/api/v1/auth/register', json={'email': f'qa-{uuid4().hex}@example.com', 'password': 'testing-accounts-12345', 'display_name': 'Test Fan'})
    assert result.status_code == 201, result.text


def test_analysis_access_reports_daily_allowance_and_tokens() -> None:
    with TestClient(app) as client:
        sign_in(client)
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
        sign_in(client)
        response = client.post("/api/v1/analysis/not-a-real-personalized-match/rich")
        assert response.status_code == 404
        assert "personalized match feed" in response.json()["detail"]


def test_rich_analysis_uses_server_fixture_and_model_context(monkeypatch) -> None:
    from app.api import analysis as analysis_api

    monkeypatch.setattr(analysis_api.settings, "openrouter_api_key", "test-key")
    match_id = f"server-grounding-{uuid4().hex}"

    async def fixture(db, user, requested_match_id):
        assert requested_match_id == match_id
        return {
            "id": requested_match_id,
            "home_team": {"id": "10", "name": "Server Home"},
            "away_team": {"id": "20", "name": "Server Away"},
            "competition": {"name": "Server League"},
        }

    class Provider:
        async def get_recent_results(self, team_id, limit=5):
            return []

    async def model(requested_match_id, home_name=None, away_name=None, competition=None):
        assert requested_match_id == match_id
        assert home_name == "Server Home"
        assert away_name == "Server Away"
        assert competition == "Server League"
        return {
            "available": True,
            "pick": "HOME",
            "probabilities": {"HOME": 0.5, "DRAW": 0.3, "AWAY": 0.2},
        }

    captured = {}

    async def explain(**kwargs):
        captured.update(kwargs)
        return "Server-grounded explanation"

    monkeypatch.setattr(analysis_api, "_find_personalized_match", fixture)
    monkeypatch.setattr(analysis_api, "get_football_provider", lambda: Provider())
    monkeypatch.setattr(analysis_api, "predict_match", model)
    monkeypatch.setattr(analysis_api, "explain_match", explain)
    monkeypatch.setattr(
        analysis_api,
        "analysis_access_summary",
        lambda db, user_id: {"tokens": 0, "free_remaining": 1, "date": "2026-10-07"},
    )
    monkeypatch.setattr(
        analysis_api,
        "unlock_analysis",
        lambda db, user_id, requested_match_id, analysis_text=None: {
            "unlocked": True,
            "source": "FREE_DAILY",
            "charged": True,
            "tokens": 0,
            "free_remaining": 0,
            "date": "2026-10-07",
        },
    )

    with TestClient(app) as client:
        sign_in(client)
        response = client.post(f"/api/v1/analysis/{match_id}/rich")

    assert response.status_code == 200
    assert captured, "explain_match was not called"
    assert captured["home_team"] == "Server Home"
    assert captured["away_team"] == "Server Away"
    assert captured["model_outlook"]["pick"] == "HOME"


def test_match_unlock_status_is_scoped_to_match() -> None:
    with TestClient(app) as client:
        sign_in(client)
        first = client.get("/api/v1/analysis/access?match_id=never-unlocked")
        second = client.get("/api/v1/analysis/access")
        assert first.status_code == 200
        assert first.json()["match_unlocked"] is False
        assert second.status_code == 200
        assert second.json()["match_unlocked"] is False


def test_existing_match_unlock_is_reported_without_charging_again() -> None:
    from app.database.session import get_db
    from app.models.analysis import MatchAnalysisUnlock

    with TestClient(app) as client:
        sign_in(client)
        db = next(get_db())
        try:
            from app.api.auth import require_user
            from sqlalchemy import select
            from app.models.user import User
            user = db.scalar(select(User).order_by(User.id.desc()))
            assert user is not None
            match_id = f"reopen-{uuid4().hex}"
            db.add(MatchAnalysisUnlock(user_id=user.id, match_id=match_id, unlock_source="FREE_DAILY", unlock_date="2026-10-08"))
            db.commit()
            response = client.get(f"/api/v1/analysis/access?match_id={match_id}")
            other = client.get("/api/v1/analysis/access?match_id=another-match")
            assert response.status_code == 200
            assert response.json()["match_unlocked"] is True
            assert other.json()["match_unlocked"] is False
        finally:
            db.close()
