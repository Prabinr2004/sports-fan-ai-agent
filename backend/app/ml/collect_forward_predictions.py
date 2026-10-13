"""Collect research forecasts from approved local domestic production artifacts.

Reads a user-supplied fixtures JSON array; never fetches fixtures or results.
Uses the exact v2 feature mapping in app.ml.trained. Only future UTC dates
are accepted. Does not touch production models or databases.

Example fixtures file:
[{"competition":"laliga","date":"2026-11-01",
  "home":"Real Madrid CF","away":"FC Barcelona"}]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from app.ml.forward_validation import read_json, record
from app.ml.trained import predict_from_team_names, PRODUCTION_MODEL_VERSION

DOMESTIC = tuple(PRODUCTION_MODEL_VERSION)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fixtures-json", type=Path, required=True)
    p.add_argument("--ledger", type=Path, default=Path("app/ml/artifacts/forward_predictions.json"))
    p.add_argument("--dry-run", action="store_true", help="Preview forecasts without saving")
    args = p.parse_args()
    fixtures = read_json(args.fixtures_json, [])
    if not isinstance(fixtures, list):
        p.error("Fixtures file must contain a JSON array")
    today = datetime.now(timezone.utc).date()
    saved = skipped = 0
    for fixture in fixtures:
        try:
            league = fixture["competition"]
            day = fixture["date"]
            home = fixture["home"]
            away = fixture["away"]
            if league not in DOMESTIC:
                raise ValueError("Only five domestic leagues supported; European model requires a separate feature pipeline")
            if datetime.strptime(day, "%Y-%m-%d").date() <= today:
                raise ValueError("Fixture date must be in the future (UTC)")
            prediction = predict_from_team_names(home, away, league)
            if prediction is None:
                raise ValueError("No matching local artifact/team states; cannot generate a reliable forecast")
            version = prediction["model_version"]
            if not version.endswith("-v2"):
                raise ValueError(f"Expected production v2 artifact; found {version}")
            probabilities = prediction["probabilities"]
            print(json.dumps({"fixture": fixture, "model": version, "probabilities": probabilities,
                              "warning": "Uses saved artifact team states, which may be stale; verify data snapshot before interpreting results."}, indent=2))
            if not args.dry_run:
                record(SimpleNamespace(
                    ledger=args.ledger, competition=league, date=day, home=home, away=away,
                    model_id=version, home_prob=probabilities["HOME"],
                    draw_prob=probabilities["DRAW"], away_prob=probabilities["AWAY"]))
                saved += 1
        except (KeyError, TypeError, ValueError, OSError) as exc:
            skipped += 1
            print(f"SKIPPED: {fixture!r}: {exc}")
    print(f"Completed: saved={saved}, skipped={skipped}, dry_run={args.dry_run}")


if __name__ == "__main__":
    main()
