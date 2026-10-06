from types import SimpleNamespace

from app.services.prediction_results import parse_utc


def _is_complete_prediction(row) -> bool:
    has_real_teams = bool(
        row.home_team_name
        and row.away_team_name
        and row.home_team_name.strip().casefold() != "home"
        and row.away_team_name.strip().casefold() != "away"
    )
    return has_real_teams and parse_utc(row.kickoff_utc) is not None


def test_real_prediction_metadata_is_complete():
    row = SimpleNamespace(
        home_team_name="FC Barcelona",
        away_team_name="Getafe CF",
        kickoff_utc="2026-10-10T16:30:00Z",
    )
    assert _is_complete_prediction(row)


def test_placeholder_prediction_metadata_is_incomplete():
    row = SimpleNamespace(
        home_team_name="Home",
        away_team_name="Away",
        kickoff_utc=None,
    )
    assert not _is_complete_prediction(row)
