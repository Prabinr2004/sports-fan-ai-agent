import httpx
import pytest

from app.api import teams


@pytest.mark.asyncio
async def test_missing_section_failure_enters_cooldown(monkeypatch, tmp_path):
    monkeypatch.setattr(teams, "_CACHE_DB", tmp_path / "sections.db")
    attempts = 0

    async def unavailable(team_id):
        nonlocal attempts
        attempts += 1
        request = httpx.Request("GET", "https://example.test/teams")
        response = httpx.Response(429, request=request)
        raise httpx.HTTPStatusError("rate limit", request=request, response=response)

    first, notice = await teams._cached_section(unavailable, "86", "squad")
    second, retry_notice = await teams._cached_section(unavailable, "86", "squad")
    assert first == second == []
    assert notice
    assert retry_notice
    assert attempts == 1


@pytest.mark.asyncio
async def test_saved_section_survives_failed_refresh(monkeypatch, tmp_path):
    monkeypatch.setattr(teams, "_CACHE_DB", tmp_path / "sections.db")
    attempts = 0

    async def provider(team_id):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return [{"id": "player1"}]
        request = httpx.Request("GET", "https://example.test/teams")
        response = httpx.Response(429, request=request)
        raise httpx.HTTPStatusError("rate limit", request=request, response=response)

    first, _ = await teams._cached_section(provider, "86", "squad")
    second, notice = await teams._cached_section(provider, "86", "squad", force=True)
    assert first == second
    assert notice
    assert attempts == 2
