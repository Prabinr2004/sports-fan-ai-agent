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


@pytest.mark.asyncio
async def test_failed_retry_never_returns_null_section(monkeypatch, tmp_path):
    monkeypatch.setattr(teams, "_CACHE_DB", tmp_path / "sections.db")
    attempts = 0

    async def unavailable(team_id):
        nonlocal attempts
        attempts += 1
        request = httpx.Request("GET", "https://example.test/teams")
        response = httpx.Response(429, request=request)
        raise httpx.HTTPStatusError("rate limit", request=request, response=response)

    first, _ = await teams._cached_section(unavailable, "86", "fixtures")
    assert first == []
    with teams._cache_db() as db:
        db.execute("UPDATE team_sections SET retry_after=0 WHERE team_id=? AND section=?", ("86", "fixtures"))
    second, notice = await teams._cached_section(unavailable, "86", "fixtures")
    assert second == []
    assert isinstance(second, list)
    assert notice
    assert attempts == 2


@pytest.mark.asyncio
async def test_saved_section_cooldown_displays_stale_notice(monkeypatch, tmp_path):
    monkeypatch.setattr(teams, "_CACHE_DB", tmp_path / "sections.db")
    teams._write_section("86", "squad", [{"id": "player1"}])
    teams._backoff_section("86", "squad")
    calls = 0

    async def provider(team_id):
        nonlocal calls
        calls += 1
        return []

    data, notice = await teams._cached_section(provider, "86", "squad")
    assert data == [{"id": "player1"}]
    assert "saved" in notice.lower()
    assert calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (401, "authentication"),
        (403, "denied"),
        (404, "not available"),
        (429, "rate limit"),
    ],
)
async def test_optional_team_section_explains_provider_status(status_code, expected):
    async def unavailable(team_id):
        request = httpx.Request("GET", "https://example.test/teams/86/squad")
        response = httpx.Response(status_code, request=request)
        raise httpx.HTTPStatusError("provider error", request=request, response=response)

    data, notice = await teams._optional_provider_call(unavailable, "86")
    assert data == []
    assert expected in notice.lower()
