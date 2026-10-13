from app.services.quiz_selection import (
    QuizBankExhausted, question_history_key, select_unseen_questions,
)


def test_all_twelve_rounds_use_each_question_once():
    bank = [{"id": f"q{i}"} for i in range(60)]
    seen = set()
    for round_number in range(12):
        chosen = select_unseen_questions(bank, seen, seed=f"user:1:round:{round_number}")
        assert len(chosen) == 5
        assert not ({q["id"] for q in chosen} & seen)
        seen.update(q["id"] for q in chosen)
    assert len(seen) == 60


def test_exhaustion_never_repeats_questions():
    bank = [{"id": f"q{i}"} for i in range(60)]
    try:
        select_unseen_questions(bank, {f"q{i}" for i in range(56)}, seed="test")
    except QuizBankExhausted:
        pass
    else:
        assert False, "Expected exhaustion error"


def test_history_scope():
    assert question_history_key(1, None) == question_history_key(1, "barcelona")
    assert question_history_key(2, "madrid") != question_history_key(2, "barcelona")
    assert question_history_key(3, "madrid") != question_history_key(2, "madrid")


def test_duplicate_ids_are_rejected():
    try:
        select_unseen_questions([{"id": "a"}, {"id": "a"}], set(), count=1, seed="test")
    except ValueError:
        pass
    else:
        assert False, "Expected duplicate-ID error"


def test_club_round_counts_are_isolated():
    from unittest.mock import MagicMock
    from app.api.quiz import new_quiz_rounds

    db = MagicMock()
    db.execute.return_value.all.return_value = [
        (1, None, 7),
        (2, "madrid", 8),
        (2, "barcelona", 3),
        (3, "madrid", 2),
        (3, "barcelona", 1),
    ]
    assert new_quiz_rounds(db, 42, "madrid") == {1: 7, 2: 8, 3: 2}
    assert new_quiz_rounds(db, 42, "barcelona") == {1: 7, 2: 3, 3: 1}
    assert new_quiz_rounds(db, 42) == {1: 7, 2: 8, 3: 2}


def test_global_unlock_does_not_sum_clubs():
    from unittest.mock import MagicMock
    from app.api.quiz import new_quiz_rounds
    from app.services.quiz_progression import unlocked_level

    db = MagicMock()
    db.execute.return_value.all.return_value = [
        (1, None, 7), (2, "madrid", 4), (2, "barcelona", 4),
    ]
    assert new_quiz_rounds(db, 42)[2] == 4
    assert unlocked_level(new_quiz_rounds(db, 42)) == 2
