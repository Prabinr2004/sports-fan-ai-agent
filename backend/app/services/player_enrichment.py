"""Optional TheSportsDB player artwork and shirt-number enrichment.

Never replace the primary football-data.org squad. Match only when a name is
unambiguous; prefer matching birth dates when available.
"""
from datetime import datetime, timedelta, timezone
import re
import sqlite3
from pathlib import Path
import unicodedata

import httpx

TEAM_IDS = {
    "real madrid": 133738, "real madrid cf": 133738,
    "liverpool": 133602, "liverpool fc": 133602,
    "manchester united": 133612, "manchester united fc": 133612,
    "manchester city": 133613, "manchester city fc": 133613,
    "arsenal": 133604, "arsenal fc": 133604,
    "barcelona": 133739, "fc barcelona": 133739,
}
_TEAM_CACHE = {}
_TEAM_CACHE_TTL = timedelta(days=7)
_CACHE = {}
_CACHE_TTL = timedelta(hours=12)
_SEARCH_CACHE = {}
_MAX_SEARCHES_PER_TEAM = 8
_DB_PATH = Path(__file__).resolve().parents[2] / "player_artwork_cache.sqlite3"

def _db():
    db = sqlite3.connect(_DB_PATH, timeout=5)
    db.execute("CREATE TABLE IF NOT EXISTS player_artwork (team_id TEXT NOT NULL, player_key TEXT NOT NULL, photo_url TEXT, shirt_number INTEGER, PRIMARY KEY(team_id, player_key))")
    return db

def _saved_artwork(team_id, player):
    try:
        with _db() as db:
            return db.execute("SELECT photo_url, shirt_number FROM player_artwork WHERE team_id=? AND player_key=?", (str(team_id), _normalize(player.get("name")))).fetchone()
    except sqlite3.Error:
        return None

def _save_artwork(team_id, player, photo, number):
    if not photo and number is None:
        return
    try:
        with _db() as db:
            db.execute("INSERT INTO player_artwork (team_id, player_key, photo_url, shirt_number) VALUES (?, ?, ?, ?) ON CONFLICT(team_id, player_key) DO UPDATE SET photo_url=COALESCE(excluded.photo_url, photo_url), shirt_number=COALESCE(excluded.shirt_number, shirt_number)", (str(team_id), _normalize(player.get("name")), photo, number))
    except sqlite3.Error:
        pass



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


async def _resolve_team_id(team):
    """Resolve TheSportsDB ID, never assume IDs match football-data.org."""
    name = str(team.get("name") or "").strip()
    key = _normalize(name)
    if not key:
        return None
    known = TEAM_IDS.get(name.lower())
    if known:
        return known
    now = datetime.now(timezone.utc)
    cached = _TEAM_CACHE.get(key)
    if cached and now - cached[0] < _TEAM_CACHE_TTL:
        return cached[1]

    # The free API may return only one search result; accept only a unique,
    # exact team name/alternate-name match in the Soccer sport.
    result = None
    try:
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=False) as client:
            response = await client.get(
                "https://www.thesportsdb.com/api/v1/json/123/searchteams.php",
                params={"t": name},
            )
            response.raise_for_status()
            teams = (response.json() or {}).get("teams") or []
        matches = [
            item for item in teams
            if isinstance(item, dict)
            and _normalize(item.get("strSport")) in {"soccer", "football"}
            and key in {
                _normalize(item.get("strTeam")),
                _normalize(item.get("strTeamAlternate")),
            }
            and str(item.get("idTeam") or "").isdigit()
        ]
        if len(matches) == 1:
            result = int(matches[0]["idTeam"])
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        pass
    # Cache misses as well: a restricted free API must not be hammered.
    _TEAM_CACHE[key] = (now, result)
    return result


async def enrich_squad(team, squad, refresh_missing=False):
    if not squad:
        return squad
    team_id = await _resolve_team_id(team)
    if not team_id:
        return squad
    squad = [dict(player) for player in squad]
    for player in squad:
        saved = _saved_artwork(team_id, player)
        if saved:
            player["photo_url"] = player.get("photo_url") or saved[0]
            if player.get("shirt_number") is None:
                player["shirt_number"] = saved[1]
    if all(player.get("photo_url") and player.get("shirt_number") is not None for player in squad):
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

    # The free team-list API only returns a subset. Search a small number of
    # missing players by name, respecting the free API's 30 requests/minute.
    missing = [p for p in squad if (not p.get("photo_url") or p.get("shirt_number") is None) and not _match(p, players)]
    searched = 0
    for player in missing:
        if searched >= _MAX_SEARCHES_PER_TEAM:
            break
        name = str(player.get("name") or "").strip()
        key = (team_id, _normalize(name))
        if not key[1]:
            continue
        cached = _SEARCH_CACHE.get(key)
        if cached and now - cached[0] < _CACHE_TTL and not refresh_missing:
            candidates = cached[1]
        else:
            searched += 1
            try:
                async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                    response = await client.get(
                        "https://www.thesportsdb.com/api/v1/json/123/searchplayers.php",
                        params={"p": name},
                    )
                    response.raise_for_status()
                    payload = response.json()
                candidates = payload.get("player") or []
                if not isinstance(candidates, list):
                    candidates = []
                _SEARCH_CACHE[key] = (now, candidates)
            except (httpx.HTTPError, ValueError, TypeError):
                # Avoid retry storms when the optional provider is unavailable.
                _SEARCH_CACHE[key] = (now, [])
                continue
        # A player search can return namesakes from other clubs. Require the
        # same TheSportsDB team ID, or an exact matching birth date.
        verified = [
            item for item in candidates
            if isinstance(item, dict) and (
                str(item.get("idTeam") or "") == str(team_id)
                or (
                    _date(player.get("date_of_birth"))
                    and _date(item.get("dateBorn")) == _date(player.get("date_of_birth"))
                )
            )
        ]
        match = _match(player, verified)
        if match:
            players.append(match)

    enriched = []
    for player in squad:
        updated = dict(player)
        candidate = _match(player, players)
        if candidate:
            image = candidate.get("strCutout") or candidate.get("strThumb")
            if isinstance(image, str) and image.startswith("https://") and "thesportsdb.com/" in image.split("/")[2] + "/":
                updated["photo_url"] = image
            number = candidate.get("strNumber")
            if updated.get("shirt_number") is None and str(number or "").strip().isdigit() and 0 <= int(number) <= 99:
                updated["shirt_number"] = int(number)
        _save_artwork(team_id, player, updated.get('photo_url'), updated.get('shirt_number'))
        enriched.append(updated)
    return enriched
