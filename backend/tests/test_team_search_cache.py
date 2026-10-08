import httpx
import pytest

from app.api import teams
from app.services import team_search_cache


@pytest.mark.asyncio
async def test_search_uses_cache_and_stale_results_on_provider_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(team_search_cache, "DB_PATH", tmp_path / "search.db")
    calls = []

    class Provider:
        async def search_teams(self, q):
            calls.append(q)
            if len(calls) > 1:
                request = httpx.Request("GET", "https://example.test/teams")
                response = httpx.Response(429, request=request)
                raise httpx.HTTPStatusError("rate limited", request=request, response=response)
            return [{"id": "86", "name": "Real Madrid"}]

    monkeypatch.setattr(teams, "get_football_provider", lambda: Provider())
    first = await teams.search_teams("Real Madrid")
    second = await teams.search_teams(" real   madrid ")
    assert first["results"] == second["results"]
    assert second["cached"] is True
    assert len(calls) == 1

    with team_search_cache._connect() as db:
        db.execute("UPDATE team_search_cache SET saved_at=0")

    stale = await teams.search_teams("Real Madrid")
    assert stale["results"] == first["results"]
    assert stale["cached"] is True
    assert "notice" in stale
    assert len(calls) == 2

    backoff = await teams.search_teams("Real Madrid")
    assert backoff["cached"] is True
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_search_without_cache_returns_provider_error(monkeypatch, tmp_path):
    monkeypatch.setattr(team_search_cache, "DB_PATH", tmp_path / "empty.db")

    class Provider:
        async def search_teams(self, q):
            request = httpx.Request("GET", "https://example.test/teams")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    monkeypatch.setattr(teams, "get_football_provider", lambda: Provider())
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await teams.search_teams("Barcelona")
    assert exc.value.status_code == 502
