from abc import ABC, abstractmethod
from typing import Any


class FootballProvider(ABC):
    """Contract every football-data provider must satisfy."""

    @abstractmethod
    async def search_teams(self, query: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_team(self, provider_team_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_squad(self, provider_team_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_fixtures(self, provider_team_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_match(self, provider_match_id: str) -> dict[str, Any]:
        raise NotImplementedError
