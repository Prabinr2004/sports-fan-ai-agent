from __future__ import annotations

"""Audit StatsBomb Open Data before we build an xG-based FanSphere model.

This intentionally does not change production. It downloads the official open-data
competition index and reports men's club league seasons available for research.
"""

import json
from pathlib import Path
import httpx

COMPETITIONS_URL = "https://raw.githubusercontent.com/hudl/open-data/master/data/competitions.json"
TARGETS = {"Premier League", "La Liga", "1. Bundesliga", "Serie A", "Ligue 1"}


def audit() -> dict:
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(COMPETITIONS_URL)
        response.raise_for_status()
        rows = response.json()

    coverage: dict[str, list[dict]] = {name: [] for name in sorted(TARGETS)}
    for row in rows:
        name = row.get("competition_name")
        if name not in TARGETS:
            continue
        if row.get("competition_gender") != "male" or row.get("competition_international"):
            continue
        coverage[name].append({
            "competition_id": row.get("competition_id"),
            "season_id": row.get("season_id"),
            "season_name": row.get("season_name"),
            "match_available": row.get("match_available"),
            "match_available_360": row.get("match_available_360"),
        })

    for seasons in coverage.values():
        seasons.sort(key=lambda item: str(item.get("season_name", "")))

    return {
        "source": "StatsBomb Open Data (hudl/open-data)",
        "purpose": "coverage audit for a future event/xG research experiment",
        "coverage": coverage,
        "decision_rule": (
            "Do not replace FanSphere's five-league production training data with this source "
            "unless coverage is sufficiently recent and broad. Sparse seasons may instead be "
            "used to prototype event-derived/xG features and validate whether they add signal."
        ),
    }


if __name__ == "__main__":
    result = audit()
    out = Path(__file__).resolve().parent / "artifacts" / "statsbomb_coverage_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
