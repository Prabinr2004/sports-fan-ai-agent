"""Isolated regression checks for FanSphere rewards and progression.

Run from backend: python -m unittest discover -s tests -p 'test_rewards_safety.py' -v
Uses in-memory SQLite only. No API calls or production database access.
"""
import unittest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.session import Base
from app.models.progress import DailyActivity, XPEvent
from app.models.gems import GemEvent
from app.models.analysis import AnalysisDailyClaim, AnalysisTokenEvent, MatchAnalysisUnlock
from app.models.user import User
from app.services.progress import streak_summary, level_from_xp
from app.services.gems import exchange_xp, gem_balance, spendable_xp
from app.services.analysis_access import unlock_analysis, analysis_access_summary
from app.services.quiz_progression import unlocked_level, can_play_rewarded, level_progress


class RewardsSafetyTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        user = User(email="test-only@example.invalid", display_name="Test", password_hash="test")
        self.db.add(user)
        self.db.commit()
        self.user_id = user.id

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def earn(self, amount):
        self.db.add(XPEvent(user_id=self.user_id, amount=amount,
                            source_type="test_reward", source_id=str(amount)))
        self.db.commit()

    def test_levels_and_unlocks(self):
        self.assertEqual(unlocked_level({1: 6, 2: 0}), 1)
        self.assertEqual(unlocked_level({1: 7, 2: 0}), 2)
        self.assertEqual(unlocked_level({1: 7, 2: 7}), 3)
        self.assertTrue(can_play_rewarded(2, {2: 11}, 2))
        self.assertFalse(can_play_rewarded(2, {2: 12}, 2))
        self.assertFalse(can_play_rewarded(4, {}, 3))
        self.assertEqual(level_progress(1, {1: 6}, 1)["rounds_to_unlock_next"], 1)

    def test_xp_level(self):
        self.assertEqual(level_from_xp(499)["level"], 1)
        self.assertEqual(level_from_xp(500)["level"], 2)

    def test_streaks(self):
        today = date.today()
        for offset in (3, 2, 1):
            self.db.add(DailyActivity(user_id=self.user_id, activity_date=today - timedelta(days=offset)))
        self.db.commit()
        result = streak_summary(self.db, self.user_id, today)
        self.assertEqual(result["current_streak"], 3)
        self.assertEqual(result["longest_streak"], 3)
        self.db.add(DailyActivity(user_id=self.user_id, activity_date=today))
        self.db.commit()
        self.assertEqual(streak_summary(self.db, self.user_id, today)["current_streak"], 4)
        self.assertEqual(streak_summary(self.db, self.user_id, today + timedelta(days=2))["current_streak"], 0)

    def test_gem_exchange_and_insufficient_xp(self):
        self.earn(600)
        result = exchange_xp(self.db, self.user_id, 2)
        self.assertEqual(result["xp_spent"], 400)
        self.assertEqual(gem_balance(self.db, self.user_id), 2)
        self.assertEqual(spendable_xp(self.db, self.user_id), 200)
        with self.assertRaises(ValueError):
            exchange_xp(self.db, self.user_id, 2)
        self.assertEqual(gem_balance(self.db, self.user_id), 2)

    def test_free_then_paid_analysis_and_no_double_charge(self):
        first = unlock_analysis(self.db, self.user_id, "fixture-one", "analysis one")
        self.assertTrue(first["unlocked"])
        self.assertEqual(first["source"], "FREE_DAILY")
        self.assertEqual(analysis_access_summary(self.db, self.user_id)["free_remaining"], 0)
        again = unlock_analysis(self.db, self.user_id, "fixture-one")
        self.assertFalse(again["charged"])
        self.assertEqual(again["source"], "FREE_DAILY")
        denied = unlock_analysis(self.db, self.user_id, "fixture-two")
        self.assertFalse(denied["unlocked"])
        self.db.add(GemEvent(user_id=self.user_id, amount=8, source_type="test", source_id="seed"))
        self.db.commit()
        for index in range(3):
            result = unlock_analysis(self.db, self.user_id, f"paid-{index}")
            self.assertTrue(result["unlocked"])
            self.assertEqual(result["source"], "GEMS")
        self.assertEqual(gem_balance(self.db, self.user_id), 2)
        denied = unlock_analysis(self.db, self.user_id, "paid-four")
        self.assertFalse(denied["unlocked"])
        self.assertEqual(gem_balance(self.db, self.user_id), 2)


if __name__ == "__main__":
    unittest.main()
