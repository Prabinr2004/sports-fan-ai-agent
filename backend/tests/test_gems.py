from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.database.session import SessionLocal
from app.models.progress import XPEvent
from app.models.analysis import MatchAnalysisUnlock
from app.services.analysis_access import analysis_access_summary, unlock_analysis


def register(client):
    email = f"gems-{uuid4().hex}@example.com"
    response = client.post("/api/v1/auth/register", json={
        "email": email, "password": "testing-accounts-12345", "display_name": "Gem Tester"
    })
    assert response.status_code == 201, response.text
    return response.json()["user"]["id"]


def test_exchange_requires_earned_xp():
    with TestClient(app) as client:
        register(client)
        result = client.post("/api/v1/economy/exchange", json={"gems": 1})
        assert result.status_code == 400
        wallet = client.get("/api/v1/economy").json()
        assert wallet["gems"] == 0


def test_exchange_and_daily_extra_analysis_limit():
    with TestClient(app) as client:
        user_id = register(client)
        with SessionLocal() as db:
            db.add(XPEvent(user_id=user_id, amount=1400, source_type="test_reward", source_id=uuid4().hex))
            db.commit()

        response = client.post("/api/v1/economy/exchange", json={"gems": 6})
        assert response.status_code == 200, response.text
        assert response.json()["gems"] == 6
        assert response.json()["spendable_xp"] == 200

        with SessionLocal() as db:
            first = unlock_analysis(db, user_id, f"match-{uuid4().hex}", "Test")
            assert first["source"] == "FREE_DAILY"
            for _ in range(3):
                result = unlock_analysis(db, user_id, f"match-{uuid4().hex}", "Test")
                assert result["unlocked"] and result["source"] == "GEMS"
            blocked = unlock_analysis(db, user_id, f"match-{uuid4().hex}", "Test")
            assert not blocked["unlocked"]
            summary = analysis_access_summary(db, user_id)
            assert summary["gems"] == 0
            assert summary["extra_remaining"] == 0
            assert summary["free_remaining"] == 0
            assert db.scalars(select(MatchAnalysisUnlock).where(MatchAnalysisUnlock.user_id == user_id)).all()
