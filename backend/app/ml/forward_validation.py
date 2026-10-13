"""Research-only forward prediction ledger (no network or production writes).

Record predictions before fixtures, then score them after results appear in
existing local OpenFootball rows JSON. This does not generate predictions:
enter probabilities from a candidate model's pre-match output.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.ml.training import LEAGUES, normalize_team_name

COMPETITIONS = tuple(LEAGUES) + ("europe",)
LABELS = ("HOME", "DRAW", "AWAY")


def read_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def fixture_id(competition, match_date, home, away):
    return "|".join((competition, match_date, normalize_team_name(home), normalize_team_name(away)))


def record(args):
    today = datetime.now(timezone.utc).date()
    match_day = date.fromisoformat(args.date)
    if match_day <= today:
        raise ValueError("Forward entries require a future UTC fixture date")
    probabilities = [args.home_prob, args.draw_prob, args.away_prob]
    if any(p < 0 or p > 1 for p in probabilities) or abs(sum(probabilities) - 1) > 1e-5:
        raise ValueError("Probabilities must each be 0..1 and sum to 1")
    ledger = read_json(args.ledger, [])
    key = fixture_id(args.competition, args.date, args.home, args.away)
    if any(r["fixture_id"] == key and r["model_id"] == args.model_id for r in ledger):
        raise ValueError("Already recorded this fixture and model; no overwriting pre-match predictions")
    entry = {
        "fixture_id": key, "competition": args.competition,
        "date": args.date, "home": args.home, "away": args.away,
        "model_id": args.model_id, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "probabilities": dict(zip(LABELS, probabilities)),
    }
    ledger.append(entry)
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    args.ledger.write_text(json.dumps(ledger, indent=2) + "\n")
    print(json.dumps(entry, indent=2))


def evaluate(args):
    ledger = read_json(args.ledger, [])
    rows = read_json(args.results_json, [])
    results = {}
    for row in rows:
        if not all(k in row for k in ("date", "home", "away", "hg", "ag")):
            continue
        key = fixture_id(args.competition, str(row["date"])[:10], row["home"], row["away"])
        results[key] = row
    by_model = {}
    for entry in ledger:
        if entry["competition"] != args.competition:
            continue
        row = results.get(entry["fixture_id"])
        if row is None:
            continue
        # Match-day granularity is not enough to establish kickoff ordering.
        # Requiring an earlier UTC date prevents same-day after-result entries.
        if entry["recorded_at_utc"][:10] >= entry["date"]:
            continue
        hg, ag = int(row["hg"]), int(row["ag"])
        outcome = "HOME" if hg > ag else "AWAY" if ag > hg else "DRAW"
        p = entry["probabilities"]
        import math
        logloss = -math.log(max(1e-12, p[outcome]))
        brier = sum((p[k] - (1 if k == outcome else 0)) ** 2 for k in LABELS)
        correct = max(LABELS, key=lambda k: p[k]) == outcome
        bucket = by_model.setdefault(entry["model_id"], {"matches": 0, "correct": 0, "log_loss_total": 0., "brier_total": 0., "draws": 0})
        bucket["matches"] += 1
        bucket["correct"] += int(correct)
        bucket["log_loss_total"] += logloss
        bucket["brier_total"] += brier
        bucket["draws"] += int(outcome == "DRAW")
    report = {
        "competition": args.competition,
        "results_file": str(args.results_json),
        "models": {
            model: {
                "matches": s["matches"],
                "accuracy": s["correct"] / s["matches"],
                "log_loss": s["log_loss_total"] / s["matches"],
                "brier": s["brier_total"] / s["matches"],
                "actual_draw_rate": s["draws"] / s["matches"],
            }
            for model, s in sorted(by_model.items())
        },
        "note": "Compare models only on identical fixtures; these summaries can have different coverage. Data is offline and research-only.",
    }
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=Path("app/ml/artifacts/forward_predictions.json"))
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("record", help="Save immutable pre-match probabilities")
    r.add_argument("--competition", choices=COMPETITIONS, required=True)
    r.add_argument("--date", required=True, help="UTC fixture date YYYY-MM-DD")
    r.add_argument("--home", required=True)
    r.add_argument("--away", required=True)
    r.add_argument("--model-id", required=True)
    r.add_argument("--home-prob", type=float, required=True)
    r.add_argument("--draw-prob", type=float, required=True)
    r.add_argument("--away-prob", type=float, required=True)
    e = sub.add_parser("evaluate", help="Score saved predictions using local completed matches")
    e.add_argument("--competition", choices=COMPETITIONS, required=True)
    e.add_argument("--results-json", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "record":
        record(args)
    else:
        evaluate(args)


if __name__ == "__main__":
    main()
