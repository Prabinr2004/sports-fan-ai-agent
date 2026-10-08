"""Optional TheSportsDB player artwork and shirt-number enrichment.

Never replace the primary football-data.org squad. Match only when a name is
unambiguous; prefer matching birth dates when available.
"""
from datetime import datetime, timedelta, timezone
import re
import unicodedata

import httpx

TEAM_IDS = {"real madrid": 133738, "real madrid cf": 133738, "liverpool": 133602, "liverpool fc": 133602}
_CACHE = {}
_CACHE_TTL = timedelta(hours=12)


def _normalize(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _date(value):
    return str(value or "")[:10]


def _match(player, candidates):
    name = _normalize(player.get("name"))
    dob = _date(player.get("date_of_birth"))
    if not name:
        return None
    matches = []
    for item in candidates:
        other = _normalize(item.get("strPlayer"))
        if not other:
            continue
        other_dob = _date(item.get("dateBorn"))
        if dob and other_dob and dob != other_dob:
            continue
        # Only use partial/alternate names when birth dates confirm identity.
        aliases = [item.get("strPlayer"), item.get("strPlayerAlternate")]
        exact_alias = any(_normalize(alias) == name for alias in aliases if alias)
        player_parts = [_normalize(part) for part in str(player.get("name") or "").split()]
        provider_parts = [_normalize(part) for part in str(item.get("strPlayer") or "").split()]
        shared_surname = bool(player_parts and provider_parts and player_parts[-1] == provider_parts[-1] and len(player_parts[-1]) >= 5)
        confirmed_partial = bool(dob and other_dob and dob == other_dob and shared_surname)
        if exact_alias or confirmed_partial:
            matches.append(item)
    return matches[0] if len(matches) == 1 else None


async def enrich_squad(team, squad):
    if not squad:
        return squad
    team_id = TEAM_IDS.get(str(team.get("name") or "").strip().lower())
    if not team_id:
        return squad
    now = datetime.now(timezone.utc)
    entry = _CACHE.get(team_id)
    if entry and now - entry[0] < _CACHE_TTL:
        players = entry[1]
    else:
        try:
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=False) as client:
                response = await client.get(
                    "https://www.thesportsdb.com/api/v1/json/123/lookup_all_players.php",
                    params={"id": team_id},
                )
                response.raise_for_status()
                payload = response.json()
            players = payload.get("player") or []
            if not isinstance(players, list):
                return squad
            _CACHE[team_id] = (now, players)
        except (httpx.HTTPError, ValueError, TypeError):
            return squad

    enriched = []
    for player in squad:
        updated = dict(player)
        candidate = _match(player, players)
        if candidate:
            image = candidate.get("strCutout") or candidate.get("strThumb")
            if isinstance(image, str) and image.startswith("https://") and "thesportsdb.com/" in image.split("/")[2] + "/":
                updated["photo_url"] = image
            number = candidate.get("strNumber")
            if str(number or "").strip().isdigit() and 0 <= int(number) <= 99:
                updated["shirt_number"] = int(number)
        enriched.append(updated)
    return enriched
