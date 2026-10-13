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


def test_quiz_level_boundaries_do_not_advance_early():
    assert quiz_level_from_completions(9) == 2
    assert quiz_level_from_completions(14) == 3
    assert quiz_level_from_completions(19) == 4


# New three-level progression policy (kept separate from the legacy API until migration).
from app.services.quiz_progression import (
    can_play_rewarded, level_progress, unlocked_level,
)


def test_new_seven_round_unlock_allows_earlier_level():
    counts = {1: 7, 2: 0, 3: 0}
    assert unlocked_level(counts) == 2
    assert can_play_rewarded(1, counts, 2)
    assert can_play_rewarded(2, counts, 2)
    assert not can_play_rewarded(3, counts, 2)


def test_new_level_three_unlock_and_twelve_round_cap():
    counts = {1: 12, 2: 7, 3: 0}
    assert unlocked_level(counts) == 3
    assert not can_play_rewarded(1, counts, 3)
    assert can_play_rewarded(2, counts, 3)
    assert can_play_rewarded(3, counts, 3)


def test_new_progress_preserves_existing_unlocks():
    assert unlocked_level({1: 0, 2: 0}, legacy_unlocked_level=3) == 3
    result = level_progress(1, {1: 7}, 2)
    assert result["rounds_remaining"] == 5
    assert result["rounds_to_unlock_next"] == 0
    assert result["next_level_unlocked"] is True


def test_unlock_boundaries_and_completed_rounds():
    for completed in range(7):
        assert unlocked_level({1: completed, 2: 0}) == 1
    assert unlocked_level({1: 7, 2: 0}) == 2
    for completed in range(7):
        assert unlocked_level({1: 7, 2: completed}) == 2
    assert unlocked_level({1: 7, 2: 7}) == 3
    assert not can_play_rewarded(2, {1: 7, 2: 12}, 3)
    assert can_play_rewarded(1, {1: 7, 2: 12}, 3)


def test_unlocked_level_switch_does_not_change_rounds():
    rounds = {1: 8, 2: 7, 3: 1}
    for chosen in (1, 2, 3):
        assert can_play_rewarded(chosen, rounds, unlocked_level(rounds))
    assert rounds == {1: 8, 2: 7, 3: 1}
