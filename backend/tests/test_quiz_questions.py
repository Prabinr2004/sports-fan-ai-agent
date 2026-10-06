from app.services.quiz_questions import shuffle_options


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
