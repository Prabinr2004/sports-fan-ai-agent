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
SEASONS = [2022, 2023, 2024, 2025, 2026]
EXPECTED_MIN = {
    "EPL": 300,
    "La Liga": 300,
    "Bundesliga": 250,
    "Serie A": 300,
    "Ligue 1": 250,
}


def fetch_league(slug: str, season: int):
    page_url = f"{BASE}/league/{slug}/{season}"
    api_url = f"{BASE}/getLeagueData/{slug}/{season}"
    with httpx.Client(headers=HEADERS, timeout=45.0, follow_redirects=True) as client:
        # Understat requires a cookie-setting page request before the JSON endpoint.
        page = client.get(page_url)
        page.raise_for_status()
        response = client.get(api_url)
        response.raise_for_status()
        payload = response.json()

    matches = payload.get("dates")
    if not isinstance(matches, list):
        raise RuntimeError(f"Understat returned no dates list from {api_url}")
    return matches

