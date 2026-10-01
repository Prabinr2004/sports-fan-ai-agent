from __future__ import annotations

import time
from typing import Any

import httpx

from app.providers.football.base import FootballProvider


class FootballDataOrgProvider(FootballProvider):
    """football-data.org v4 adapter.

    The rest of the application talks only to the FootballProvider contract so
    the upstream provider can be replaced later without rewriting API routes.
    """

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
            response = await client.get(
                f"{self.base_url}{path}",
                headers=self.headers,
                params=params,
            )
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

    async def _all_accessible_teams(self) -> list[dict[str, Any]]:
        if self._team_cache and time.monotonic() < self._team_cache_expires_at:
            return self._team_cache

        payload = await self._get("/teams", params={"limit": 500})
        self._team_cache = payload.get("teams", [])
        self._team_cache_expires_at = time.monotonic() + 900
        return self._team_cache

    async def search_teams(self, query: str) -> list[dict[str, Any]]:
        teams = await self._all_accessible_teams()
        needle = query.casefold().strip()

        matches = []
        for team in teams:
            searchable = " ".join(
                str(team.get(key) or "") for key in ("name", "shortName", "tla")
            ).casefold()
            if needle in searchable:
                matches.append(self._normalize_team(team))

        matches.sort(
            key=lambda team: (
                0 if (team.get("name") or "").casefold().startswith(needle) else 1,
                team.get("name") or "",
            )
        )
        return matches[:12]

    async def get_team(self, provider_team_id: str) -> dict[str, Any]:
        payload = await self._get(f"/teams/{provider_team_id}")
        return self._normalize_team(payload)

    async def get_squad(self, provider_team_id: str) -> list[dict[str, Any]]:
        payload = await self._get(f"/teams/{provider_team_id}")
        return [
            {
                "id": str(player.get("id")),
                "name": player.get("name"),
                "position": player.get("position"),
                "date_of_birth": player.get("dateOfBirth"),
                "nationality": player.get("nationality"),
            }
            for player in payload.get("squad", [])
        ]

    async def get_fixtures(self, provider_team_id: str) -> list[dict[str, Any]]:
        payload = await self._get(
            f"/teams/{provider_team_id}/matches",
            params={"status": "SCHEDULED", "limit": 10},
        )
        return [
            {
                "id": str(match.get("id")),
                "utc_date": match.get("utcDate"),
                "status": match.get("status"),
                "competition": (match.get("competition") or {}).get("name"),
                "home_team": self._normalize_team(match.get("homeTeam") or {}),
                "away_team": self._normalize_team(match.get("awayTeam") or {}),
            }
            for match in payload.get("matches", [])
        ]
