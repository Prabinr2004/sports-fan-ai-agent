from fastapi import APIRouter, Query

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/search")
async def search_teams(q: str = Query(min_length=2, max_length=100)) -> dict:
    # Provider integration arrives in Milestone 3.
    # Keeping this route now gives the frontend a stable contract.
    return {
        "query": q,
        "results": [],
        "provider_connected": False,
    }
