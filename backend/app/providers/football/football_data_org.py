from __future__ import annotations

import time
from typing import Any

import httpx

from app.providers.football.base import FootballProvider


class FootballDataOrgProvider(FootballProvider):
    """football-data.org v4 adapter."""

    def __init__(self, api_key: str, base_url: str = "https://api.football-data.org/v4") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._team_cache: list[dict[str, Any]] = []
        self._team_cache_expires_at = 0.0

    @property
    def headers(self) -> dict[str, str]:
        return {"X-Auth-Token": self.api_key}

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{self.base_url}{path}", headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _normalize_team(team: dict[str, Any]) -> dict[str, Any]:
        area = team.get("area") or {}
        running_competitions = team.get("runningCompetitions") or []
        competition = running_competitions[0] if running_competitions else {}
        return {
            "id": str(team.get("id")),
            "name": team.get("name"),
            "short_name": team.get("shortName"),
            "tla": team.get("tla"),
            "country": area.get("name"),
            "league_name": competition.get("name"),
            "crest_url": team.get("crest"),
            "venue": team.get("venue"),
            "founded": team.get("founded"),
            "club_colors": team.get("clubColors"),
            "website": team.get("website"),
        }

    @classmethod
    def _normalize_match(cls, match: dict[str, Any]) -> dict[str, Any]:
        score = match.get("score") or {}
        full_time = score.get("fullTime") or {}
        return {
            "id": str(match.get("id")),
            "utc_date": match.get("utcDate"),
            "status": match.get("status"),
            "competition": (match.get("competition") or {}).get("name"),
            "home_team": cls._normalize_team(match.get("homeTeam") or {}),
            "away_team": cls._normalize_team(match.get("awayTeam") or {}),
            "score": {"home": full_time.get("home"), "away": full_time.get("away")},
        }

    async def _all_accessible_teams(self) -> list[dict[str, Any]]:
        if self._team_cache and time.monotonic() < self._team_cache_expires_at:
            return self._team_cache
        payload = await self._get("/teams", params={"limit": 500})
        self._team_cache = payload.get("teams", [])
        self._team_cache_expires_at = time.monotonic() + 900
        return self._team_cache

    async def _cached_team_by_id(self, provider_team_id: str) -> dict[str, Any] | None:
        teams = await self._all_accessible_teams()
        return next((team for team in teams if str(team.get("id")) == str(provider_team_id)), None)

    async def search_teams(self, query: str) -> list[dict[str, Any]]:
        teams = await self._all_accessible_teams()
        needle = query.casefold().strip()
        matches = []
        for team in teams:
            searchable = " ".join(str(team.get(key) or "") for key in ("name", "shortName", "tla")).casefold()
            if needle in searchable:
                matches.append(self._normalize_team(team))
        matches.sort(key=lambda team: (0 if (team.get("name") or "").casefold().startswith(needle) else 1, team.get("name") or ""))
        return matches[:12]

    async def get_team(self, provider_team_id: str) -> dict[str, Any]:
        try:
            payload = await self._get(f"/teams/{provider_team_id}")
            return self._normalize_team(payload)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                cached = await self._cached_team_by_id(provider_team_id)
                if cached is not None:
                    return self._normalize_team(cached)
            raise

    async def get_squad(self, provider_team_id: str) -> list[dict[str, Any]]:
        payload = await self._get(f"/teams/{provider_team_id}")
        return [{"id": str(player.get("id")), "name": player.get("name"), "position": player.get("position"), "date_of_birth": player.get("dateOfBirth"), "nationality": player.get("nationality")} for player in payload.get("squad", [])]

    async def get_fixtures(self, provider_team_id: str) -> list[dict[str, Any]]:
        payload = await self._get(f"/teams/{provider_team_id}/matches", params={"status": "SCHEDULED", "limit": 10})
        return [self._normalize_match(match) for match in payload.get("matches", [])]

    async def get_match(self, provider_match_id: str) -> dict[str, Any]:
        payload = await self._get(f"/matches/{provider_match_id}")
        return self._normalize_match(payload)
