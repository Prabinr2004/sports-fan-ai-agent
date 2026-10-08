import httpx
from fastapi import APIRouter, HTTPException, Query, status

from app.services.football import get_football_provider
from app.services.player_enrichment import enrich_squad
from app.services.team_fallback import fallback_team

router = APIRouter(prefix="/teams", tags=["teams"])


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
    try:
        results = await provider.search_teams(q)
    except httpx.HTTPStatusError as exc:
        raise _provider_error(exc) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the football provider.",
        ) from exc

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
async def get_team(team_id: str) -> dict:
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

    squad, squad_notice = await _optional_provider_call(provider.get_squad, team_id)
    squad = await enrich_squad(team, squad)
    fixtures, fixtures_notice = await _optional_provider_call(provider.get_fixtures, team_id)
    recent_results, recent_notice = await _optional_provider_call(provider.get_recent_results, team_id)
    standings, standings_notice = await _optional_provider_call(provider.get_team_standings, team_id)
    scorers, scorers_notice = await _optional_provider_call(provider.get_team_scorers, team_id)

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
