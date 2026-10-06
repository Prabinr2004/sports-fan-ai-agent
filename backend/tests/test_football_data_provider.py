from app.providers.football.football_data_org import FootballDataOrgProvider


def test_normalize_team_uses_running_competition():
    team = {
        "id": 86,
        "name": "Real Madrid CF",
        "shortName": "Real Madrid",
        "tla": "RMA",
        "area": {"name": "Spain"},
        "runningCompetitions": [{"id": 2014, "name": "Primera Division"}],
        "crest": "crest.svg",
    }

    result = FootballDataOrgProvider._normalize_team(team)

    assert result["id"] == "86"
    assert result["league_name"] == "Primera Division"
    assert result["country"] == "Spain"


def test_normalize_match_keeps_score_and_competition():
    match = {
        "id": 1,
        "utcDate": "2026-10-10T19:00:00Z",
        "status": "FINISHED",
        "competition": {"name": "Primera Division"},
        "homeTeam": {"id": 86, "name": "Real Madrid CF"},
        "awayTeam": {"id": 81, "name": "FC Barcelona"},
        "score": {"fullTime": {"home": 2, "away": 1}},
    }

    result = FootballDataOrgProvider._normalize_match(match)

    assert result["competition"] == "Primera Division"
    assert result["score"] == {"home": 2, "away": 1}
    assert result["home_team"]["id"] == "86"
