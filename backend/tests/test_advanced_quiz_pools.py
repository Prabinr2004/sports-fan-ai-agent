"""Check that advanced daily quiz pools are usable and distinct."""
from app.api.quiz import fallback_question_pool, level_question_pool


def test_advanced_level_question_banks():
    ids_across_levels = set()
    for level in (3, 4, 5):
        pool = fallback_question_pool(level)
        assert len(pool) >= 25
        assert len({q["id"] for q in pool}) == len(pool)
        assert len({q["question"] for q in pool}) == len(pool)
        assert all(q["min_level"] == level for q in pool)
        assert all(len(q["options"]) == 4 for q in pool)
        assert all(len(set(q["options"])) == 4 for q in pool)
        assert all(0 <= q["answer"] < 4 for q in pool)
        assert not (ids_across_levels & {q["id"] for q in pool})
        ids_across_levels.update(q["id"] for q in pool)


def test_advanced_fallback_available_for_any_team():
    for level in (3, 4, 5):
        assert len(level_question_pool(level, {"id": 1, "name": "FC Barcelona"})) >= 25
        assert len(level_question_pool(level, {"id": 2, "name": "Real Madrid CF"})) >= 25
