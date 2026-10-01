import httpx
from fastapi import APIRouter, HTTPException, Query, status

from app.services.football import get_football_provider

router = APIRouter(prefix="/teams", tags=["teams"])


def _provider_error(exc: httpx.HTTPStatusError) -> HTTPException:
    upstream_status = exc.response.status_code
    if upstream_status in {401, 403}:
        detail = "Football provider rejected the API key or plan access."
    elif upstream_status == 429:
        detail = "Football provider rate limit reached. Try again shortly."
    else:
        detail = "Football provider request failed."
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


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

    return {
        "query": q,
        "results": results,
        "provider_connected": True,
    }


@router.get("/{team_id}")
async def get_team(team_id: str) -> dict:
    provider = get_football_provider()
    try:
        team = await provider.get_team(team_id)
        squad = await provider.get_squad(team_id)
        fixtures = await provider.get_fixtures(team_id)
    except httpx.HTTPStatusError as exc:
        raise _provider_error(exc) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the football provider.",
        ) from exc

    return {
        "team": team,
        "squad": squad,
        "fixtures": fixtures,
        "provider_connected": True,
    }
