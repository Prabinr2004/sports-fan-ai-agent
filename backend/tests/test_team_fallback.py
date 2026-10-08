import httpx
import pytest

from app.services import team_fallback


@pytest.mark.asyncio
async def test_fallback_returns_partial_data_with_clear_notices(monkeypatch):
    async def fake_get(endpoint, team_id):
        assert team_id == 133738
        if endpoint == "lookupteam.php":
            return {"teams": [{"idTeam": "133738", "strSport": "Soccer", "strTeam": "Real Madrid", "strBadge": "https://example.org/badge.png"}]}
        return {"player": [{"idTeam": "133738", "idPlayer": "123", "strPlayer": "Example Player", "strNumber": "7", "strPosition": "Forward"}]}

    monkeypatch.setattr(team_fallback, "_get", fake_get)
    result = await team_fallback.fallback_team("86")
    assert result["team"]["id"] == "86"
    assert len(result["squad"]) == 1
    assert result["squad"][0]["shirt_number"] == 7
    assert result["provider_connected"] is False
    assert "NOT the full current squad" in result["notices"]["squad"]
    assert result["fixtures"] == []


@pytest.mark.asyncio
async def test_fallback_does_not_guess_unknown_team():
    assert await team_fallback.fallback_team("999999") is None


@pytest.mark.asyncio
async def test_fallback_rejects_wrong_sport(monkeypatch):
    async def fake_get(endpoint, team_id):
        return {"teams": [{"idTeam": "133612", "strSport": "Basketball", "strTeam": "Wrong"}]}

    monkeypatch.setattr(team_fallback, "_get", fake_get)
    assert await team_fallback.fallback_team("66") is None
