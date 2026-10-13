"""Authenticated quiz integration checks using isolated newly registered test users."""
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_daily_quiz_rewards_only_once_and_keeps_one_round():
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/register", json={
            "email": f"quiz-{uuid4().hex}@example.com",
            "display_name": "Quiz Reward Test",
            "password": "secure-test-password-2026",
        })
        assert response.status_code == 201, response.text

        reset = client.post("/api/v1/quiz/progress/reset")
        assert reset.status_code == 200, reset.text
        daily = client.get("/api/v1/quiz/daily")
        assert daily.status_code == 200, daily.text
        assert len(daily.json()["questions"]) == 5
        answers = [0] * 5
        first = client.post("/api/v1/quiz/daily/submit", json={"answers": answers})
        assert first.status_code == 200, first.text
        assert first.json()["xp_awarded"] >= 50
        second = client.post("/api/v1/quiz/daily/submit", json={"answers": answers})
        assert second.status_code == 200, second.text
        assert second.json()["xp_awarded"] == 0
        assert second.json()["already_rewarded"] is True

        levels = client.get("/api/v1/quiz/levels")
        assert levels.status_code == 200, levels.text
        assert levels.json()["levels"][0]["rounds_completed"] == 1
        assert client.post("/api/v1/quiz/progress/reset").status_code == 409
