from __future__ import annotations

import time
from typing import Any

import httpx

from app.providers.football.base import FootballProvider


class FootballDataOrgProvider(FootballProvider):
    """football-data.org v4 adapter with process-local TTL caching."""

    def __init__(self, api_key: str, base_url: str = "https://api.football-data.org/v4") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    @property
    def headers(self) -> dict[str, str]:
        return {"X-Auth-Token": self.api_key}

    @staticmethod
    def _cache_key(path: str, params: dict[str, Any] | None) -> str:
        values = tuple(sorted((params or {}).items()))
        return f"{path}:{values}"

    async def _get(self, path: str, params: dict[str, Any] | None = None, ttl: int = 300) -> dict[str, Any]:
        key = self._cache_key(path, params)
        now = time.monotonic()
        cached = self._cache.get(key)
        if cached and cached[0] > now:
            return cached[1]
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(f"{self.base_url}{path}", headers=self.headers, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            # A previously successful response is still better than failing the UI
            # when the free provider temporarily rate-limits us.
            if exc.response.status_code == 429 and cached:
                return cached[1]
            raise
        self._cache[key] = (now + ttl, payload)
        return payload

    @staticmethod
    def _normalize_team(team: dict[str, Any]) -> dict[str, Any]:
        area = team.get("area") or {}; running = team.get("runningCompetitions") or []; competition = running[0] if running else {}
        return {"id": str(team.get("id")), "name": team.get("name"), "short_name": team.get("shortName"), "tla": team.get("tla"), "country": area.get("name"), "league_name": competition.get("name"), "crest_url": team.get("crest"), "venue": team.get("venue"), "founded": team.get("founded"), "club_colors": team.get("clubColors"), "website": team.get("website")}

    @classmethod
    def _normalize_match(cls, match: dict[str, Any]) -> dict[str, Any]:
        score = match.get("score") or {}; full_time = score.get("fullTime") or {}
        return {"id": str(match.get("id")), "utc_date": match.get("utcDate"), "status": match.get("status"), "competition": (match.get("competition") or {}).get("name"), "home_team": cls._normalize_team(match.get("homeTeam") or {}), "away_team": cls._normalize_team(match.get("awayTeam") or {}), "score": {"home": full_time.get("home"), "away": full_time.get("away")}}

    async def _all_accessible_teams(self) -> list[dict[str, Any]]:
        return (await self._get("/teams", params={"limit": 500}, ttl=1800)).get("teams", [])

    async def _cached_team_by_id(self, provider_team_id: str) -> dict[str, Any] | None:
        teams = await self._all_accessible_teams(); return next((team for team in teams if str(team.get("id")) == str(provider_team_id)), None)

    async def search_teams(self, query: str) -> list[dict[str, Any]]:
        teams = await self._all_accessible_teams(); needle = query.casefold().strip(); matches = []
        for team in teams:
            searchable = " ".join(str(team.get(key) or "") for key in ("name", "shortName", "tla")).casefold()
            if needle in searchable: matches.append(self._normalize_team(team))
        matches.sort(key=lambda team: (0 if (team.get("name") or "").casefold().startswith(needle) else 1, team.get("name") or "")); return matches[:12]

    async def get_team(self, provider_team_id: str) -> dict[str, Any]:
        try:
            return self._normalize_team(await self._get(f"/teams/{provider_team_id}", ttl=1800))
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                cached = await self._cached_team_by_id(provider_team_id)
                if cached is not None: return self._normalize_team(cached)
            raise

    async def get_squad(self, provider_team_id: str) -> list[dict[str, Any]]:
        payload = await self._get(f"/teams/{provider_team_id}", ttl=1800)
        return [{"id": str(p.get("id")), "name": p.get("name"), "position": p.get("position"), "date_of_birth": p.get("dateOfBirth"), "nationality": p.get("nationality")} for p in payload.get("squad", [])]

    async def get_fixtures(self, provider_team_id: str) -> list[dict[str, Any]]:
        payload = await self._get(f"/teams/{provider_team_id}/matches", params={"status": "SCHEDULED", "limit": 10}, ttl=300)
        return [self._normalize_match(m) for m in payload.get("matches", [])]

    async def get_match(self, provider_match_id: str) -> dict[str, Any]:
        return self._normalize_match(await self._get(f"/matches/{provider_match_id}", ttl=300))

    async def get_team_standings(self, provider_team_id: str) -> list[dict[str, Any]]:
        raw_team = await self._get(f"/teams/{provider_team_id}", ttl=1800)
        competitions = raw_team.get("runningCompetitions") or []
        standings: list[dict[str, Any]] = []
        for competition in competitions:
            competition_id = competition.get("id")
            if not competition_id:
                continue
            try:
                payload = await self._get(f"/competitions/{competition_id}/standings", ttl=900)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in {403, 404}:
                    continue
                raise
            for standing in payload.get("standings", []):
                table = standing.get("table") or []
                row = next((item for item in table if str((item.get("team") or {}).get("id")) == str(provider_team_id)), None)
                if row is None:
                    continue
                standings.append({
                    "competition_id": str(competition_id),
                    "competition": (payload.get("competition") or {}).get("name") or competition.get("name"),
                    "type": standing.get("type"),
                    "stage": standing.get("stage"),
                    "group": standing.get("group"),
                    "position": row.get("position"),
                    "played": row.get("playedGames"),
                    "won": row.get("won"),
                    "drawn": row.get("draw"),
                    "lost": row.get("lost"),
                    "points": row.get("points"),
                    "goals_for": row.get("goalsFor"),
                    "goals_against": row.get("goalsAgainst"),
                    "goal_difference": row.get("goalDifference"),
                })
                break
        return standings

    async def get_recent_results(self, provider_team_id: str, limit: int = 8) -> list[dict[str, Any]]:
        payload = await self._get(f"/teams/{provider_team_id}/matches", params={"status": "FINISHED", "limit": limit}, ttl=21600)
        matches = [self._normalize_match(m) for m in payload.get("matches", [])]
        matches.sort(key=lambda m: m.get("utc_date") or "")
        return matches[-limit:]
