from datetime import datetime, timedelta, timezone

from app.services.prediction_results import actual_outcome, parse_utc, result_check_due


NOW = datetime(2026, 10, 7, 20, 0, tzinfo=timezone.utc)


def test_actual_outcome_requires_finished_match():
    assert actual_outcome({"status": "IN_PLAY", "score": {"home": 2, "away": 1}}) is None


def test_actual_outcome_handles_home_away_and_draw():
    assert actual_outcome({"status": "FINISHED", "score": {"home": 2, "away": 1}}) == "HOME"
    assert actual_outcome({"status": "FINISHED", "score": {"home": 0, "away": 1}}) == "AWAY"
    assert actual_outcome({"status": "FINISHED", "score": {"home": 1, "away": 1}}) == "DRAW"


def test_result_check_is_not_due_before_kickoff_or_after_scoring():
    assert not result_check_due("PENDING", "2026-10-07T21:00:00Z", None, NOW)
    assert not result_check_due("CORRECT", "2026-10-07T18:00:00Z", None, NOW)


def test_result_check_is_due_after_kickoff_when_never_checked():
    assert result_check_due("PENDING", "2026-10-07T18:00:00Z", None, NOW)


def test_result_check_uses_cooldown():
    recent = NOW - timedelta(minutes=10)
    old = NOW - timedelta(minutes=31)
    assert not result_check_due("PENDING", "2026-10-07T18:00:00Z", recent, NOW)
    assert result_check_due("PENDING", "2026-10-07T18:00:00Z", old, NOW)


def test_parse_utc_rejects_invalid_values():
    assert parse_utc(None) is None
    assert parse_utc("not-a-date") is None


def test_naive_result_check_timestamp_is_treated_as_utc():
    naive_old = datetime(2026, 10, 7, 18, 0)
    assert result_check_due("PENDING", "2026-10-07T17:00:00Z", naive_old, NOW)


def test_missing_score_cannot_be_scored():
    assert actual_outcome({"status": "FINISHED", "score": {"home": None, "away": 1}}) is None
