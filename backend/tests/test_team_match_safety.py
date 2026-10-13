"""Offline tests for team hub caching, saved teams, and match access.

Run from backend:
    python -m unittest discover -s tests -p 'test_team_match_safety.py' -v

No provider network calls, persistent SQLite files, or production model changes.
"""
import asyncio
import time
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.session import Base
from app.models.user import User, UserFavoriteTeam
from app.models.team import Team
from app.api import teams, matches


class TeamMatchSafetyTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:",
                                    connect_args={"check_same_thread": False},
                                    poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.user = User(email="offline-team-test@example.invalid",
                         display_name="Offline test", password_hash="test")
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def add_team(self, provider_id, name):
        team = Team(provider_id=provider_id, name=name)
        self.db.add(team)
        self.db.commit()
        self.db.refresh(team)
        return team

    def test_saved_team_ids_deduplicate_primary_and_favorites(self):
        primary = self.add_team("86", "Real Madrid")
        second = self.add_team("81", "Barcelona")
        self.user.primary_team_id = primary.id
        self.db.add_all([
            UserFavoriteTeam(user_id=self.user.id, team_id=primary.id),
            UserFavoriteTeam(user_id=self.user.id, team_id=second.id),
        ])
        self.db.commit()
        self.assertEqual(matches._saved_team_ids(self.db, self.user), ["86", "81"])

    def test_saved_team_ids_limit_to_six(self):
        team_ids = []
        for i in range(8):
            team = self.add_team(str(100 + i), f"Club {i}")
            team_ids.append(team.provider_id)
            self.db.add(UserFavoriteTeam(user_id=self.user.id, team_id=team.id))
        self.db.commit()
        self.assertEqual(matches._saved_team_ids(self.db, self.user), team_ids[:6])

    def test_fixture_payload_locks_after_kickoff(self):
        future = {"id": "future", "utc_date": "2099-01-01T12:00:00Z"}
        past = {"id": "past", "utc_date": "2020-01-01T12:00:00Z"}
        self.assertFalse(matches._fixture_payload(future, "86")["prediction_locked"])
        self.assertTrue(matches._fixture_payload(past, "86")["prediction_locked"])

    def test_optional_section_handles_provider_rate_limit(self):
        request = httpx.Request("GET", "https://example.invalid/team")
        response = httpx.Response(429, request=request)
        async def rate_limited(_):
            raise httpx.HTTPStatusError("rate limited", request=request, response=response)
        result, notice = asyncio.run(teams._optional_provider_call(rate_limited, "86"))
        self.assertEqual(result, [])
        self.assertIn("rate limit", notice.lower())

    def test_cached_section_fresh_and_stale_fallback(self):
        fresh = (["cached squad"], time.time(), 0)
        with patch.object(teams, "_read_section", return_value=fresh), \
             patch.object(teams, "_optional_provider_call", new_callable=AsyncMock) as provider:
            data, notice = asyncio.run(teams._cached_section(provider, "86", "squad"))
            self.assertEqual(data, ["cached squad"])
            self.assertIsNone(notice)
            provider.assert_not_awaited()

        stale = (["older squad"], time.time() - 100000, 0)
        with patch.object(teams, "_read_section", return_value=stale), \
             patch.object(teams, "_optional_provider_call", new_callable=AsyncMock,
                          return_value=([], "Provider unavailable")), \
             patch.object(teams, "_backoff_section") as backoff:
            data, notice = asyncio.run(teams._cached_section(lambda _: None, "86", "squad"))
            self.assertEqual(data, ["older squad"])
            self.assertIn("saved data", notice)
            backoff.assert_called_once()

    def test_personalized_match_uses_followed_team(self):
        primary = self.add_team("86", "Real Madrid")
        self.user.primary_team_id = primary.id
        self.db.commit()
        provider = type("Provider", (), {})()
        provider.get_fixtures = AsyncMock(return_value=[
            {"id": "match-123", "home_team": {"id": "86"}, "away_team": {"id": "81"}}
        ])
        with patch.object(matches, "get_football_provider", return_value=provider):
            found = asyncio.run(matches._find_personalized_match(self.db, self.user, "match-123"))
            missing = asyncio.run(matches._find_personalized_match(self.db, self.user, "other"))
        self.assertEqual(found["id"], "match-123")
        self.assertIsNone(missing)
        self.assertEqual(provider.get_fixtures.await_count, 2)


if __name__ == "__main__":
    unittest.main()
