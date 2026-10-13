"""Research-only European v3 feature experiment; never changes production.

Uses locally saved historical rows from europe_historical_rows.json. Both
baseline and candidates use identical chronological train/validation/test rows.
Competition features are known before kickoff. No live API calls.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.europe_training import build_examples
from app.ml.europe_offline_benchmark import metrics

COMPETITIONS = ("cl", "el", "conf")
QUALIFIERS = ("clq", "elq", "confq")


def feature_matrix(x, meta):
    """Append pre-match competition context and conservative Elo interactions."""
    context = []
    for row in meta:
        source = row["competition_file"].removesuffix(".txt")
        family = source.removesuffix("q")
        context.append([
            float(family == "cl"),
            float(family == "el"),
            float(family == "conf"),
            float(source in QUALIFIERS),
        ])
    c = np.asarray(context, dtype=float)
    # Elo difference and recent form are already in x; interactions may
    # express different importance of team strength in qualifying rounds.
    elo_difference = np.clip(x[:, 12] / 400.0, -3.0, 3.0)
    form_difference = x[:, 0] - x[:, 1]
    return np.column_stack([
        x, c,
        elo_difference * c[:, 3],
        form_difference * c[:, 3],
    ])


def model(c):
    return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=3000))


def run(rows):
    rows = sorted(rows, key=lambda r: (str(r["date"]), r.get("source_file", ""), r["home"], r["away"]))
    x, y, meta, _ = build_examples(rows)
    n = len(y)
    a, b = int(.65 * n), int(.80 * n)
    if a < 100 or b-a < 40 or n-b < 40:
        raise ValueError("Insufficient historical rows")
    richer = feature_matrix(x, meta)
    variants = {
        "v2_features_c025": (x, .25),
        "v3_context_c005": (richer, .05),
        "v3_context_c025": (richer, .25),
        "v3_context_c1": (richer, 1.0),
    }
    validation = {}
    for name, (features, c) in variants.items():
        fitted = model(c)
        fitted.fit(features[:a], y[:a])
        validation[name] = metrics(y[a:b], fitted.predict_proba(features[a:b]), list(fitted.classes_))
    selected = min(validation, key=lambda name: validation[name]["log_loss"])
    # Evaluate a matched baseline on the same held-out rows, not a
    # historical JSON report that might contain a different split.
    test = {}
    for name in ("v2_features_c025", selected):
        features, c = variants[name]
        fitted = model(c)
        fitted.fit(features[:b], y[:b])
        test[name] = metrics(y[b:], fitted.predict_proba(features[b:]), list(fitted.classes_))
    return {
        "experiment": "europe-v3-context-features",
        "scope": "UCL, UEL, UECL, including qualifying rounds",
        "train_rows": a, "validation_rows": b-a, "test_rows": n-b,
        "validation_first_match": meta[a], "test_first_match": meta[b],
        "test_last_match": meta[-1],
        "validation": validation, "selected": selected,
        "matched_holdout": test,
        "feature_note": "Competition identity, qualifier flag and pre-match Elo/form interactions.",
        "deployment": "None. Research-only; never writes production artifacts.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("app/ml/artifacts/europe_v3_experiment.json"))
    args = parser.parse_args()
    rows = json.loads(args.rows_json.read_text())
    for row in rows:
        if isinstance(row.get("date"), str):
            row["date"] = datetime.fromisoformat(row["date"])
    report = run(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
