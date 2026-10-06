from __future__ import annotations

"""Research-only Understat coverage audit for FanSphere ML.

Checks whether recent Big Five seasons expose sufficiently complete match-level
xG before we spend time building another model. No production artifacts change.
"""

import json
import re
import httpx

BASE = "https://understat.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE + "/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

LEAGUES = {
    "EPL": "EPL",
    "La Liga": "La_liga",
    "Bundesliga": "Bundesliga",
    "Serie A": "Serie_A",
    "Ligue 1": "Ligue_1",
}
SEASONS = [2022, 2023, 2024, 2025]
EXPECTED_MIN = {
    "EPL": 300,
    "La Liga": 300,
    "Bundesliga": 250,
    "Serie A": 300,
    "Ligue 1": 250,
}


def fetch_league(slug: str, season: int):
    url = f"{BASE}/league/{slug}/{season}"
    with httpx.Client(headers=HEADERS, timeout=45.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
    text = response.text

    # Understat has historically exposed datesData in an encoded JSON blob.
    patterns = [
        r"datesData\s*=\s*JSON\.parse\('([^']+)'\)",
        'datesData\\s*=\\s*JSON\\.parse\\(\"([^\"]+)\"\\)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            raw = bytes(match.group(1), "utf-8").decode("unicode_escape")
            return json.loads(raw)

    # Newer deployments may respond directly to AJAX-shaped requests.
    try:
        payload = response.json()
        if isinstance(payload, dict):
            for key in ("datesData", "dates", "matches"):
                if isinstance(payload.get(key), list):
                    return payload[key]
        if isinstance(payload, list):
            return payload
    except Exception:
        pass
    raise RuntimeError(f"Could not locate match data in {url}")


def summarize(matches):
    completed = []
    teams = set()
    xg_complete = 0
    for match in matches:
        if not match.get("isResult"):
            continue
        completed.append(match)
        for side in ("h", "a"):
            team = match.get(side, {}).get("title")
            if team:
                teams.add(team)
        xg = match.get("xG") or {}
        if xg.get("h") not in (None, "") and xg.get("a") not in (None, ""):
            xg_complete += 1
    return {
        "completed_matches": len(completed),
        "teams": len(teams),
        "matches_with_xg": xg_complete,
        "xg_coverage": round(xg_complete / len(completed), 4) if completed else 0.0,
    }


def main():
    report = {"source": "Understat", "seasons": {}, "production_changed": False}
    for league, slug in LEAGUES.items():
        report["seasons"][league] = {}
        for season in SEASONS:
            label = f"{season}/{str(season + 1)[-2:]}"
            try:
                stats = summarize(fetch_league(slug, season))
                stats["passes_minimum_match_check"] = stats["completed_matches"] >= EXPECTED_MIN[league]
                report["seasons"][league][label] = stats
            except Exception as exc:
                report["seasons"][league][label] = {"error": str(exc)}
            print(f"Audited {league} {label}", flush=True)

    usable = []
    for league, seasons in report["seasons"].items():
        for season, stats in seasons.items():
            if (
                stats.get("passes_minimum_match_check")
                and stats.get("xg_coverage", 0) >= 0.95
            ):
                usable.append(f"{league} {season}")
    report["usable_for_xg_experiment"] = usable
    report["decision_rule"] = (
        "Build the next chronological xG benchmark only if multiple recent league-seasons "
        "have broad completed-match coverage and at least 95% xG coverage."
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
