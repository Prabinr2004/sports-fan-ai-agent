"""Optional verified goal timeline fallback from TheSportsDB free v1 API.

Free date searches are truncated; no match is safer than a false match.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

import httpx

BASE = "https://www.thesportsdb.com/api/v1/json/123"


def _name(value: str | None) -> str:
    text = (value or "").casefold()
    text = re.sub(r"\\b(cf|fc|afc|sc|club|football|internazionale|milano)\\b", " ", text)
    return re.sub(r"[^a-z0-9]", "", text)


def _same_team(primary: str | None, alternate: str | None) -> bool:
    a, b = _name(primary), _name(alternate)
    return bool(a and b and (a == b or (len(a) >= 5 and len(b) >= 5 and (a in b or b in a)) or SequenceMatcher(None, a, b).ratio() >= 0.86))


def _minute(value: object) -> tuple[int | None, int | None]:
    parts = re.match(r"^\\s*(\\d+)(?:\\s*\\+\\s*(\\d+))?", str(value or ""))
    return (int(parts.group(1)), int(parts.group(2)) if parts.group(2) else None) if parts else (None, None)


async def lookup_goal_events(match: dict) -> list[dict]:
    """Return only verified events from an exact fixture match, never guessed events."""
    try:
        kickoff = datetime.fromisoformat((match.get("utc_date") or "").replace("Z", "+00:00"))
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        home = match["home_team"]
        away = match["away_team"]
        score = match.get("score") or {}
        async with httpx.AsyncClient(timeout=7.0) as client:
            candidates = []
            # Day boundaries may differ between providers; inspect UTC date and neighbors.
            for offset in (0, -1, 1):
                day = (kickoff + timedelta(days=offset)).date().isoformat()
                response = await client.get(f"{BASE}/eventsday.php", params={"d": day, "s": "Soccer"})
                response.raise_for_status()
                candidates.extend((response.json() or {}).get("events") or [])
            verified = []
            for event in candidates:
                if not (_same_team(home.get("name"), event.get("strHomeTeam")) and _same_team(away.get("name"), event.get("strAwayTeam"))):
                    continue
                if event.get("dateEvent") not in {(kickoff + timedelta(days=i)).date().isoformat() for i in (-1, 0, 1)}:
                    continue
                try:
                    if int(event.get("intHomeScore")) != int(score["home"]) or int(event.get("intAwayScore")) != int(score["away"]):
                        continue
                except (ValueError, TypeError, KeyError):
                    continue
                verified.append(event)
            # Ambiguous fixture identity must not lead to mismatched scorers.
            ids = {str(e.get("idEvent")) for e in verified if e.get("idEvent")}
            if len(ids) != 1:
                return []
            response = await client.get(f"{BASE}/lookuptimeline.php", params={"id": next(iter(ids))})
            response.raise_for_status()
            payload = response.json() or {}
            events = payload.get("timeline") or []
            goals = []
            for event in events:
                label = str(event.get("strTimeline") or event.get("strEvent") or "").casefold()
                if "goal" not in label or "disallowed" in label or "missed" in label:
                    continue
                player = event.get("strPlayer")
                if not player:
                    continue
                minute, extra = _minute(event.get("intTime"))
                team = event.get("strTeam")
                if _same_team(team, verified[0].get("strHomeTeam")):
                    team_id = str(home.get("id"))
                elif _same_team(team, verified[0].get("strAwayTeam")):
                    team_id = str(away.get("id"))
                else:
                    continue
                goals.append({"player_name": player, "minute": minute, "extra_time": extra, "team_id": team_id})
            return goals
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return []
