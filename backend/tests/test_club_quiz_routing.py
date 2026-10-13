"""Regression checks for Level 2 club switching and quiz progression.

Run from backend: python -m pytest tests/test_club_quiz_routing.py
"""
from app.api.quiz import level_question_pool, quiz_level_from_completions


def test_level_progress_does_not_depend_on_club():
    assert quiz_level_from_completions(0) == 1
    assert quiz_level_from_completions(5) == 2
    assert quiz_level_from_completions(9) == 2
    assert quiz_level_from_completions(10) == 3


def test_level_two_club_banks_and_fallback():
    for team, prefix in [
        ("Real Madrid", "real-madrid-l2-"),
        ("FC Barcelona", "barcelona-l2-"),
        ("Liverpool FC", "liverpool-l2-"),
        ("Arsenal FC", "arsenal-l2-"),
        ("Manchester City FC", "man-city-l2-"),
        ("Chelsea FC", "chelsea-l2-"),
        ("Manchester United FC", "manutd-l2-"),
        ("Tottenham Hotspur", "tottenham-l2-"),
        ("FC Bayern München", "bayern-l2-"),
        ("FC Internazionale Milano", "inter-l2-"),
        ("AC Milan", "ac-milan-l2-"),
    ]:
        questions = level_question_pool(2, {"id": 1, "name": team})
        assert len(questions) == 60
        assert len({q["id"] for q in questions}) == 60
        assert len({q["question"] for q in questions}) == 60
        assert all(q["id"].startswith(prefix) for q in questions)
        assert all(len(q["options"]) == 4 and len(set(q["options"])) == 4 for q in questions)
        assert all(0 <= q["answer"] < 4 for q in questions)

    fallback = level_question_pool(2, {"id": 2, "name": "Napoli"})
    assert len(fallback) == 60
    assert all(q["id"].startswith("club-knowledge-") for q in fallback)


def test_switching_clubs_changes_bank_not_level():
    level = quiz_level_from_completions(7)
    madrid = level_question_pool(level, {"id": 86, "name": "Real Madrid"})
    barca = level_question_pool(level, {"id": 81, "name": "FC Barcelona"})
    assert level == 2
    assert set(q["id"] for q in madrid).isdisjoint(q["id"] for q in barca)


def test_all_supported_clubs_keep_levels_one_two_three_separate():
    teams = [
        "Real Madrid", "FC Barcelona", "Liverpool FC", "Arsenal FC",
        "Manchester City FC", "Chelsea FC", "Manchester United FC",
        "Tottenham Hotspur", "FC Bayern München",
        "FC Internazionale Milano", "AC Milan",
    ]
    for name in teams:
        team = {"id": 1, "name": name}
        pools = {level: level_question_pool(level, team) for level in (1, 2, 3)}
        for level, questions in pools.items():
            assert len(questions) == 60, (name, level, len(questions))
            assert len({q["id"] for q in questions}) == 60, (name, level)
        for left, right in ((1, 2), (1, 3), (2, 3)):
            left_ids = {q["id"] for q in pools[left]}
            right_ids = {q["id"] for q in pools[right]}
            assert left_ids.isdisjoint(right_ids), (name, left, right)
            left_text = {q["question"].strip().casefold() for q in pools[left]}
            right_text = {q["question"].strip().casefold() for q in pools[right]}
            assert left_text.isdisjoint(right_text), (name, left, right)
