from app.api.quiz import quiz_level_from_completions


def test_quiz_starts_at_general_level():
    assert quiz_level_from_completions(0) == 1
    assert quiz_level_from_completions(4) == 1


def test_quiz_advances_every_five_rewarded_days():
    assert quiz_level_from_completions(5) == 2
    assert quiz_level_from_completions(10) == 3
    assert quiz_level_from_completions(15) == 4
    assert quiz_level_from_completions(20) == 5


def test_expert_level_is_capped():
    assert quiz_level_from_completions(100) == 5
