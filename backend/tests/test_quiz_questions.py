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
    questions = await build_team_questions("86", "Test Club", 5, "2026-10-07")

    ids = [question["id"] for question in questions]
    assert len(ids) == len(set(ids))
    assert "club-country" in ids
    assert "club-venue" in ids
    assert "club-founded" in ids
    assert "club-colors" in ids
    assert any(question_id.startswith("player-position-") for question_id in ids)
    assert any(question_id.startswith("player-nationality-") for question_id in ids)
    assert any(question_id.startswith("player-birth-year-") for question_id in ids)
    for question in questions:
        assert len(question["options"]) == 4
        assert len({option.casefold() for option in question["options"]}) == 4
        assert question["options"][question["answer"]]
