"""Offline Bundesliga/LaLiga v6 research using existing local match JSON.

Compare baseline v3 features against small, interpretable difference features.
Do not change production artifacts or call the football provider.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.training import build_examples, LEAGUES
from app.ml.europe_offline_benchmark import metrics


def augment(x):
    """Pre-match relative strength, venue form and recent scoring margins."""
    return np.column_stack((
        x,
        x[:, 0] - x[:, 1],  # recent points difference
        x[:, 4] - x[:, 5],  # home/away venue form difference
        (x[:, 6] - x[:, 8]) - (x[:, 7] - x[:, 9]),  # goal balance difference
        x[:, 10] - x[:, 11],  # ten-match goal difference
        np.clip(x[:, 14] / 400., -3., 3.) * (x[:, 4] - x[:, 5]),
    ))


def model(c):
    return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=3000))


def run(rows, league):
    if league not in ("bundesliga", "laliga"):
        raise ValueError("This experiment targets Bundesliga and LaLiga")
    rows = sorted(rows, key=lambda r: (str(r["date"]), r["home"], r["away"]))
    x, y, meta, _ = build_examples(rows)
    n = len(y)
    a, b = int(n * .70), int(n * .80)
    if a < 100 or b-a < 30 or n-b < 30:
        raise ValueError("Not enough matches")
    variants = {
        "v3_baseline_c025": (x, .25),
        "v6_relative_c005": (augment(x), .05),
        "v6_relative_c025": (augment(x), .25),
        "v6_relative_c05": (augment(x), .5),
    }
    validation = {}
    for name, (features, c) in variants.items():
        m = model(c)
        m.fit(features[:a], y[:a])
        validation[name] = metrics(y[a:b], m.predict_proba(features[a:b]), list(m.classes_))
    selected = min(validation, key=lambda name: validation[name]["log_loss"])
    # Historical holdout is already known from prior v3-v5 research;
    # do not treat this as fresh deployment evidence.
    holdout = {}
    for name in dict.fromkeys(("v3_baseline_c025", selected)):
        features, c = variants[name]
        m = model(c)
        m.fit(features[:b], y[:b])
        holdout[name] = metrics(y[b:], m.predict_proba(features[b:]), list(m.classes_))
    return {
        "league": LEAGUES[league]["name"],
        "experiment": "v6-relative-features",
        "train_rows": a, "validation_rows": b-a, "test_rows": n-b,
        "validation": validation, "selected": selected,
        "matched_retrospective_holdout": holdout,
        "first_test_match": meta[b], "last_test_match": meta[-1],
        "warning": "Research only. Previously inspected holdout; requires new forward matches for promotion.",
        "production_changes": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--league", choices=["bundesliga", "laliga"], required=True)
    p.add_argument("--rows-json", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = run(json.loads(args.rows_json.read_text()), args.league)
    output = args.output or Path(f"app/ml/artifacts/{args.league}_v6_relative.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
