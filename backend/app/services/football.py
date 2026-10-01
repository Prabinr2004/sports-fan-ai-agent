from fastapi import HTTPException, status

from app.core.config import settings
from app.providers.football.base import FootballProvider
from app.providers.football.football_data_org import FootballDataOrgProvider


def get_football_provider() -> FootballProvider:
    if not settings.football_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Football data provider is not configured yet.",
        )

    return FootballDataOrgProvider(
        api_key=settings.football_api_key,
        base_url=settings.football_api_base_url or "https://api.football-data.org/v4",
    )
