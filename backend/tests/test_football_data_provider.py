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

    assert result["competition"] == "LaLiga"
    assert result["score"] == {"home": 2, "away": 1}
    assert result["home_team"]["id"] == "86"


def test_recent_results_fills_sparse_season_without_duplicates(monkeypatch):
    import asyncio
    from datetime import date
    from unittest.mock import AsyncMock

    provider = FootballDataOrgProvider("test")
    def match(mid, when):
        return {"id": mid, "utcDate": when, "status": "FINISHED",
                "homeTeam": {"id": 1}, "awayTeam": {"id": 2},
                "score": {"fullTime": {"home": 2, "away": 1}}}
    current = {"matches": [match(5, "2026-10-01T12:00:00Z")]}
    older = {"matches": [match(i, f"2026-05-0{i}T12:00:00Z") for i in range(1, 5)]
             + [match(5, "2026-10-01T12:00:00Z")]}
    getter = AsyncMock(side_effect=[current, older])
    monkeypatch.setattr(provider, "_get", getter)
    results = asyncio.run(provider.get_recent_results("1", limit=5))
    assert len(results) == 5
    assert len({m["id"] for m in results}) == 5
    assert results[-1]["id"] == "5"
    assert getter.await_count == 2


def test_recent_results_gracefully_handles_unavailable_older_season(monkeypatch):
    import asyncio
    import httpx
    from unittest.mock import AsyncMock
    provider = FootballDataOrgProvider("test")
    current = {"matches": [{"id": 5, "utcDate": "2026-10-01T12:00:00Z",
                            "status": "FINISHED", "homeTeam": {"id": 1},
                            "awayTeam": {"id": 2},
                            "score": {"fullTime": {"home": 2, "away": 1}}}]}
    getter = AsyncMock(side_effect=[current, httpx.ConnectError("unavailable")])
    monkeypatch.setattr(provider, "_get", getter)
    results = asyncio.run(provider.get_recent_results("1", limit=5))
    assert len(results) == 1
