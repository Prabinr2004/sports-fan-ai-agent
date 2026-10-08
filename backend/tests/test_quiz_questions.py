import pytest

from app.services.quiz_questions import build_team_questions, numeric_distractors, shuffle_options


def test_shuffle_options_is_deterministic_for_daily_quiz():
    first = shuffle_options("Santiago Bernabeu", ["Anfield", "San Siro", "Old Trafford"], "2026-10-07:86:venue")
    second = shuffle_options("Santiago Bernabeu", ["Anfield", "San Siro", "Old Trafford"], "2026-10-07:86:venue")
    assert first == second


def test_shuffle_options_keeps_correct_answer_and_four_choices():
    options, answer = shuffle_options("Spain", ["England", "Germany", "Italy"], "team-country")
    assert len(options) == 4
    assert options[answer] == "Spain"


def test_shuffle_options_rejects_insufficient_unique_choices():
    options, answer = shuffle_options("Spain", ["Spain", "Spain"], "bad")
    assert options == []
    assert answer == -1


def test_shuffle_options_deduplicates_case_insensitively():
    options, answer = shuffle_options("Spain", ["spain", "England", "Germany", "Italy"], "casefold")
    assert len(options) == 4
    assert options[answer] == "Spain"
    assert len({option.casefold() for option in options}) == 4


def test_numeric_distractors_are_distinct_from_correct_year():
    values = numeric_distractors(2000)
    assert "2000" not in values
    assert len(values) == len(set(values))
    assert len(values) >= 4


@pytest.mark.asyncio
async def test_personalized_quiz_pool_expands_with_provider_backed_facts(monkeypatch):
    class Provider:
        async def get_team(self, team_id):
            return {
                "country": "Spain",
                "venue": "Test Stadium",
                "founded": 1902,
                "club_colors": "White / Gold",
            }

        async def get_squad(self, team_id):
            return [
                {"id": "1", "name": "Keeper One", "position": "Goalkeeper", "nationality": "Spain", "date_of_birth": "1998-01-01"},
                {"id": "2", "name": "Defender One", "position": "Defence", "nationality": "France", "date_of_birth": "1999-01-01"},
                {"id": "3", "name": "Midfielder One", "position": "Midfield", "nationality": "Germany", "date_of_birth": "2000-01-01"},
                {"id": "4", "name": "Forward One", "position": "Offence", "nationality": "Brazil", "date_of_birth": "2001-01-01"},
            ]

    monkeypatch.setattr("app.services.quiz_questions.get_football_provider", lambda: Provider())
    level2 = await build_team_questions("86", "Test Club", 2, "2026-10-07")
    level3 = await build_team_questions("86", "Test Club", 3, "2026-10-07")
    level5 = await build_team_questions("86", "Test Club", 5, "2026-10-07")
    assert {"club-country", "club-venue", "club-founded", "club-colors"} <= {q["id"] for q in level2}
    assert any(q["id"].startswith("player-position-") for q in level3)
    assert any(q["id"].startswith("player-nationality-") for q in level3)
    assert any(q["id"].startswith("player-birth-year-") for q in level5)
    for questions in (level2, level3, level5):
        ids = [q["id"] for q in questions]
        assert len(ids) == len(set(ids))
        for q in questions:
            assert len(q["options"]) == 4
            assert len({option.casefold() for option in q["options"]}) == 4
            assert q["options"][q["answer"]]


@pytest.mark.asyncio
@pytest.mark.parametrize("club", ["Real Madrid", "Liverpool", "Manchester United", "Barcelona"])
async def test_offline_history_and_level_separation(monkeypatch, club):
    class OfflineProvider:
        async def get_team(self, team_id):
            raise RuntimeError("provider offline")

        async def get_squad(self, team_id):
            raise RuntimeError("provider offline")

    monkeypatch.setattr("app.services.quiz_questions.get_football_provider", lambda: OfflineProvider())
    levels = {}
    for level in (2, 3, 4, 5):
        questions = await build_team_questions("86", club, level, "2026-10-07")
        assert questions, f"{club} level {level} has no offline questions"
        levels[level] = {q["id"] for q in questions}
        for q in questions:
            assert len(q["options"]) == 4
            assert 0 <= q["answer"] < 4
            assert len(set(q["options"])) == 4
    for first in levels:
        for second in levels:
            if first < second:
                assert levels[first].isdisjoint(levels[second])


@pytest.mark.asyncio
async def test_real_madrid_record_goal_answer_offline(monkeypatch):
    class OfflineProvider:
        async def get_team(self, team_id):
            raise RuntimeError("offline")

        async def get_squad(self, team_id):
            raise RuntimeError("offline")

    monkeypatch.setattr("app.services.quiz_questions.get_football_provider", lambda: OfflineProvider())
    questions = await build_team_questions("86", "Real Madrid", 5, "2026-10-07")
    record = next(q for q in questions if q["id"] == "rm-record-goals")
    assert record["options"][record["answer"]] == "450"
