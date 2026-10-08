import httpx
import sqlite3
import json
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, status

from app.services.football import get_football_provider
from app.services.player_enrichment import enrich_squad
from app.services.team_fallback import fallback_team
from app.services.team_search_cache import read_search, save_search, postpone_search, SEARCH_TTL_SECONDS

router = APIRouter(prefix="/teams", tags=["teams"])
_CACHE_DB = Path(__file__).resolve().parents[2] / "team_sections_cache.sqlite3"
_SECTION_TTL = {"squad": 86400, "fixtures": 900, "recent_results": 1800, "standings": 1800, "scorers": 1800}
_RETRY_AFTER = 180

def _cache_db():
    db = sqlite3.connect(_CACHE_DB, timeout=5)
    db.execute("CREATE TABLE IF NOT EXISTS team_sections (team_id TEXT NOT NULL, section TEXT NOT NULL, payload TEXT NOT NULL, saved_at REAL NOT NULL, retry_after REAL NOT NULL DEFAULT 0, PRIMARY KEY(team_id, section))")
    return db

def _read_section(team_id, section):
    try:
        with _cache_db() as db:
            row = db.execute("SELECT payload, saved_at, retry_after FROM team_sections WHERE team_id=? AND section=?", (str(team_id), section)).fetchone()
        return (json.loads(row[0]), row[1], row[2]) if row else None
    except (sqlite3.Error, ValueError, TypeError):
        return None

def _write_section(team_id, section, payload):
    try:
        with _cache_db() as db:
            db.execute("INSERT INTO team_sections (team_id,section,payload,saved_at,retry_after) VALUES(?,?,?,?,0) ON CONFLICT(team_id,section) DO UPDATE SET payload=excluded.payload,saved_at=excluded.saved_at,retry_after=0", (str(team_id),section,json.dumps(payload),time.time()))
    except (sqlite3.Error, TypeError, ValueError):
        pass

def _backoff_section(team_id, section):
    try:
        with _cache_db() as db:
            db.execute("UPDATE team_sections SET retry_after=? WHERE team_id=? AND section=?", (time.time()+_RETRY_AFTER,str(team_id),section))
    except sqlite3.Error:
        pass

def _cooldown_missing_section(team_id, section):
    """Remember temporary failures even when there is no previous success."""
    try:
        with _cache_db() as db:
            db.execute(
                "INSERT INTO team_sections(team_id,section,payload,saved_at,retry_after) VALUES(?,?,?,0,?) "
                "ON CONFLICT(team_id,section) DO UPDATE SET retry_after=excluded.retry_after",
                (str(team_id), section, "null", time.time() + _RETRY_AFTER),
            )
    except sqlite3.Error:
        pass

async def _cached_section(call, team_id, section, force=False):
    cached = _read_section(team_id, section)
    now = time.time()
    if cached and cached[2] > now:
        if cached[0] is None:
            return [], "Provider temporarily unavailable; retrying shortly."
        return cached[0], None
    if cached and cached[0] is not None and not force and now-cached[1] < _SECTION_TTL[section]:
        return cached[0], None
    data, notice = await _optional_provider_call(call, team_id)
    if notice:
        if cached and cached[0] is not None:
            _backoff_section(team_id, section)
            return cached[0], "Showing previously saved data; provider is temporarily unavailable."
        _cooldown_missing_section(team_id, section)
        return [], notice
    _write_section(team_id, section, data)
    return data, None



def _provider_error(exc: httpx.HTTPStatusError) -> HTTPException:
    upstream_status = exc.response.status_code
    if upstream_status == 401:
        detail = "Football provider authentication failed (401). Check FOOTBALL_API_KEY in backend/.env."
    elif upstream_status == 403:
        detail = "Football provider denied access (403). Check API plan permissions or account status."
    elif upstream_status == 429:
        detail = "Football provider rate limit reached. Try again shortly."
    else:
        detail = "Football provider request failed."
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


async def _optional_provider_call(call, team_id: str) -> tuple[list, str | None]:
    """Return optional team data without breaking the whole hub on plan limits."""
    try:
        return await call(team_id), None
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403, 404}:
            return [], "This data is unavailable for this team on the current provider plan."
        if exc.response.status_code == 429:
            return [], "Provider rate limit reached for this section."
        return [], "This section could not be loaded from the football provider."
    except httpx.HTTPError:
        return [], "This section could not reach the football provider."


@router.get("/search")
async def search_teams(q: str = Query(min_length=2, max_length=100)) -> dict:
    provider = get_football_provider()
    cached = read_search(q)
    if cached and time.time() - cached["saved_at"] < SEARCH_TTL_SECONDS:
        return {"query": q, "results": cached["results"], "provider_connected": True, "cached": True}
    if cached and cached["retry_after"] > time.time():
        return {"query": q, "results": cached["results"], "provider_connected": False, "cached": True, "notice": "Showing saved results while provider is unavailable."}
    try:
        results = await provider.search_teams(q)
    except httpx.HTTPStatusError as exc:
        if cached:
            postpone_search(q)
            return {"query": q, "results": cached["results"], "provider_connected": False, "cached": True, "notice": "Showing saved results while provider is unavailable."}
        raise _provider_error(exc) from exc
    except httpx.HTTPError as exc:
        if cached:
            postpone_search(q)
            return {"query": q, "results": cached["results"], "provider_connected": False, "cached": True, "notice": "Showing saved results while provider is unavailable."}
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the football provider.",
        ) from exc

    save_search(q, results)
    return {"query": q, "results": results, "provider_connected": True}


@router.get("/{team_id}/players/{player_id}/position")
async def get_player_position(team_id: str, player_id: str) -> dict:
    """Optional on-demand player position lookup; never invent tactical roles."""
    provider = get_football_provider()
    try:
        position = await provider.get_player_position(player_id)
        return {"player_id": player_id, "position": position, "source": "football-data.org"}
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403, 404, 429}:
            return {"player_id": player_id, "position": None, "source": "unavailable"}
        raise _provider_error(exc) from exc
    except httpx.HTTPError:
        return {"player_id": player_id, "position": None, "source": "unavailable"}


@router.get("/{team_id}")
async def get_team(team_id: str, refresh_missing_photos: bool = False, refresh_team_data: bool = False) -> dict:
    provider = get_football_provider()
    # Core club/team identity must succeed; squad and fixtures are optional because
    # football-data.org can restrict individual resources by competition/plan.
    try:
        team = await provider.get_team(team_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403, 429}:
            fallback = await fallback_team(team_id)
            if fallback is not None:
                return fallback
        raise _provider_error(exc) from exc
    except httpx.HTTPError as exc:
        fallback = await fallback_team(team_id)
        if fallback is not None:
            return fallback
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the football provider.",
        ) from exc

    squad, squad_notice = await _cached_section(provider.get_squad, team_id, "squad", force=refresh_team_data)
    squad = await enrich_squad(team, squad, refresh_missing=refresh_missing_photos)
    fixtures, fixtures_notice = await _cached_section(provider.get_fixtures, team_id, "fixtures", force=refresh_team_data)
    recent_results, recent_notice = await _cached_section(provider.get_recent_results, team_id, "recent_results", force=refresh_team_data)
    standings, standings_notice = await _cached_section(provider.get_team_standings, team_id, "standings", force=refresh_team_data)
    scorers, scorers_notice = await _cached_section(provider.get_team_scorers, team_id, "scorers", force=refresh_team_data)

    notices = {}
    if squad_notice:
        notices["squad"] = squad_notice
    if fixtures_notice:
        notices["fixtures"] = fixtures_notice
    if recent_notice:
        notices["recent_results"] = recent_notice
    if standings_notice:
        notices["standings"] = standings_notice
    if scorers_notice:
        notices["scorers"] = scorers_notice

    return {
        "team": team,
        "squad": squad,
        "fixtures": fixtures,
        "recent_results": recent_results[:5],
        "standings": standings,
        "scorers": scorers,
        "notices": notices,
        "provider_connected": True,
    }
