"""Offline integration checks for FanSphere rich analysis endpoint.

Run from backend: python -m unittest discover -s tests -p 'test_analysis_endpoint.py' -v
All calls to football and AI providers are mocked. SQLite is in-memory.
"""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.session import Base
from app.models.user import User
from app.models.gems import GemEvent
from app.api import analysis
from app.services.gems import gem_balance


FIXTURE = {
    "id": "fixture-1",
    "home_team": {"id": "86", "name": "Real Madrid"},
    "away_team": {"id": "81", "name": "Barcelona"},
    "competition": {"name": "LaLiga"},
}


class AnalysisEndpointTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.user = User(email="analysis-test@example.invalid", display_name="Test", password_hash="test")
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def call(self, match_id="fixture-1"):
        return asyncio.run(analysis.rich_match_analysis(match_id, None, self.db))

    def mocks(self, fixture=FIXTURE):
        provider = SimpleNamespace(get_recent_results=AsyncMock(return_value=[]))
        return (
            patch.object(analysis, "require_user", return_value=self.user),
            patch.object(analysis.settings, "openrouter_api_key", "offline-test-key"),
            patch.object(analysis, "_find_personalized_match", new_callable=AsyncMock, return_value=fixture),
            patch.object(analysis, "get_football_provider", return_value=provider),
            patch.object(analysis, "predict_match", new_callable=AsyncMock, return_value={"available": False}),
            patch.object(analysis, "explain_match", new_callable=AsyncMock, return_value="Offline test analysis"),
        )

    def test_first_analysis_cached_on_repeat(self):
        from contextlib import ExitStack
        with ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in self.mocks()]
            first = self.call()
            second = self.call()
            self.assertEqual(first["analysis"], "Offline test analysis")
            self.assertFalse(first["cached"])
            self.assertEqual(first["access"]["source"], "FREE_DAILY")
            self.assertTrue(second["cached"])
            self.assertFalse(second["access"]["charged"])
            self.assertEqual(mocks[-1].await_count, 1)

    def test_second_match_requires_gems(self):
        from contextlib import ExitStack
        with ExitStack() as stack:
            for p in self.mocks():
                stack.enter_context(p)
            self.call()
            with self.assertRaises(HTTPException) as caught:
                self.call("fixture-2")
            self.assertEqual(caught.exception.status_code, 402)
            self.assertEqual(gem_balance(self.db, self.user.id), 0)

    def test_ai_failure_does_not_charge(self):
        from contextlib import ExitStack
        from app.services.openrouter import AIAnalysisUnavailable
        with ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in self.mocks()]
            mocks[-1].side_effect = AIAnalysisUnavailable("Offline AI unavailable")
            with self.assertRaises(HTTPException) as caught:
                self.call()
            self.assertEqual(caught.exception.status_code, 503)
            self.assertEqual(gem_balance(self.db, self.user.id), 0)
            self.assertEqual(analysis.analysis_access_summary(self.db, self.user.id)["free_remaining"], 1)

    def test_missing_fixture_returns_404_without_ai_call(self):
        from contextlib import ExitStack
        with ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in self.mocks(fixture=None)]
            with self.assertRaises(HTTPException) as caught:
                self.call()
            self.assertEqual(caught.exception.status_code, 404)
            mocks[-1].assert_not_awaited()

    def test_unconfigured_ai_returns_503(self):
        with patch.object(analysis, "require_user", return_value=self.user), \
             patch.object(analysis.settings, "openrouter_api_key", ""):
            with self.assertRaises(HTTPException) as caught:
                self.call()
            self.assertEqual(caught.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
