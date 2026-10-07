from app.api.quiz import GENERAL_QUESTIONS, quiz_level_from_completions


def test_general_question_pool_is_large_enough_for_fresh_practice():
    assert len(GENERAL_QUESTIONS) >= 15
    ids = [question["id"] for question in GENERAL_QUESTIONS]
    assert len(ids) == len(set(ids))


def test_general_questions_have_four_options_and_valid_answers():
    for question in GENERAL_QUESTIONS:
        assert len(question["options"]) == 4
        assert 0 <= question["answer"] < 4
        assert question["options"][question["answer"]]


def test_practice_does_not_change_level_progression_contract():
    assert quiz_level_from_completions(1) == 1
    assert quiz_level_from_completions(4) == 1
    assert quiz_level_from_completions(5) == 2
