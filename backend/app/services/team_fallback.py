"""Limited, explicitly labelled club fallback for provider outages.

TheSportsDB free API only exposes a subset of players and fixtures.
Never represent fallback results as a complete/current squad or schedule.
"""
from datetime import datetime, timedelta, timezone
import httpx

# Cross-provider IDs are intentionally explicit: never confuse ID namespaces.
TEAM_MAP = {
    "86": 133738,   # Real Madrid
    "64": 133602,   # Liverpool
    "66": 133612,   # Manchester United
}
_CACHE = {}
_TTL = timedelta(hours=6)
_BASE = "https://www.thesportsdb.com/api/v1/json/123"


async def _get(endpoint, team_id):
    key = (endpoint, team_id)
    now = datetime.now(timezone.utc)
    entry = _CACHE.get(key)
    if entry and now - entry[0] < _TTL:
        return entry[1]
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
        response = await client.get(f"{_BASE}/{endpoint}", params={"id": team_id})
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Unexpected sports provider response")
    _CACHE[key] = (now, payload)
    return payload


async def fallback_team(provider_team_id):
    external_id = TEAM_MAP.get(str(provider_team_id))
    if not external_id:
        return None
    try:
        raw = (await _get("lookupteam.php", external_id)).get("teams") or []
        if not raw or not isinstance(raw[0], dict):
            return None
        item = raw[0]
        if str(item.get("idTeam")) != str(external_id) or item.get("strSport") != "Soccer":
            return None
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return None

    team = {
        "id": str(provider_team_id),
        "name": item.get("strTeam"),
        "short_name": item.get("strTeamShort") or item.get("strTeam"),
        "tla": item.get("strTeamShort"),
        "country": item.get("strCountry"),
        "league_name": item.get("strLeague"),
        "crest_url": item.get("strBadge"),
        "venue": item.get("strStadium"),
        "founded": item.get("intFormedYear"),
        "club_colors": None,
        "website": item.get("strWebsite"),
    }
    notices = {
        "squad": "Primary provider unavailable. TheSportsDB free tier returns at most 10 players; this is NOT the full current squad.",
        "fixtures": "Primary provider unavailable. Upcoming fixtures are not available in this fallback view.",
        "recent_results": "Primary provider unavailable. Recent results are not available in this fallback view.",
        "standings": "Primary provider unavailable. League standings are not available in this fallback view.",
        "scorers": "Primary provider unavailable. Scorer statistics are not available in this fallback view.",
    }
    squad = []
    try:
        players = (await _get("lookup_all_players.php", external_id)).get("player") or []
        for p in players[:10]:
            if not isinstance(p, dict) or str(p.get("idTeam")) != str(external_id):
                continue
            number = str(p.get("strNumber") or "").strip()
            squad.append({
                "id": str(p.get("idPlayer") or ""),
                "name": p.get("strPlayer"),
                "position": p.get("strPosition"),
                "date_of_birth": p.get("dateBorn"),
                "nationality": p.get("strNationality"),
                "photo_url": p.get("strCutout") or p.get("strThumb"),
                "shirt_number": int(number) if number.isdigit() and 0 <= int(number) <= 99 else None,
            })
    except (httpx.HTTPError, ValueError, TypeError):
        pass

    return {
        "team": team, "squad": squad, "fixtures": [], "recent_results": [],
        "standings": [], "scorers": [], "notices": notices,
        "provider_connected": False,
        "fallback_source": "TheSportsDB (partial, free tier)",
    }
