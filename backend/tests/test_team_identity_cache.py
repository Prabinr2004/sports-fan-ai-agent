import httpx
import pytest
from app.api import teams


@pytest.mark.asyncio
async def test_team_identity_cached_and_survives_provider_outage(monkeypatch, tmp_path):
    monkeypatch.setattr(teams, "_CACHE_DB", tmp_path / "team-cache.db")
    calls = 0

    class Provider:
        async def get_team(self, team_id):
            nonlocal calls
            calls += 1
            if calls > 1:
                request = httpx.Request("GET", "https://example.test/teams/86")
                raise httpx.ConnectError("offline", request=request)
            return {"id": str(team_id), "name": "Real Madrid"}

        async def get_squad(self, team_id): return []
        async def get_fixtures(self, team_id): return []
        async def get_recent_results(self, team_id): return []
        async def get_team_standings(self, team_id): return []
        async def get_team_scorers(self, team_id): return []

    monkeypatch.setattr(teams, "get_football_provider", lambda: Provider())

    async def no_enrichment(team, squad, refresh_missing=False):
        return squad

    monkeypatch.setattr(teams, "enrich_squad", no_enrichment)
    first = await teams.get_team("86")
    assert first["team"]["name"] == "Real Madrid"
    second = await teams.get_team("86")
    assert second["team"] == first["team"]
    assert calls == 1
    stale = await teams.get_team("86", refresh_team_data=True)
    assert stale["team"] == first["team"]
    assert stale["provider_connected"] is False
    assert "saved" in stale["notices"]["team"].lower()
    assert calls == 2
    cooldown = await teams.get_team("86", refresh_team_data=True)
    assert cooldown["team"] == first["team"]
    assert cooldown["provider_connected"] is False
    assert calls == 2  # Identity provider is not retried during its cooldown.
