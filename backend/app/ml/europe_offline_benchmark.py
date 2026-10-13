"""Offline, non-production benchmark for European match outcome models.

Provide a local JSON array of parsed historical match rows (same schema as
europe_training.download_rows). No football API or network requests are made.
The production predictor and artifacts are never modified.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.europe_training import build_examples, brier

CLASSES = ["AWAY", "DRAW", "HOME"]


def metrics(y, probabilities, classes):
    probabilities = np.asarray(probabilities)
    predicted = np.asarray(classes)[np.argmax(probabilities, axis=1)]
    return {
        "accuracy": float(accuracy_score(y, predicted)),
        "log_loss": float(log_loss(y, probabilities, labels=classes)),
        "brier": brier(y, probabilities, classes),
        "confusion_matrix_labels": list(classes),
        "confusion_matrix": confusion_matrix(y, predicted, labels=classes).tolist(),
    }


def candidates():
    return {
        "logistic_c025": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=.25, max_iter=2500)),
        "logistic_c005": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=.05, max_iter=2500)),
        "hist_gradient_boosting": lambda: HistGradientBoostingClassifier(
            learning_rate=.035, max_iter=140, max_leaf_nodes=7,
            min_samples_leaf=30, l2_regularization=3, random_state=42,
        ),
        "random_forest": lambda: RandomForestClassifier(
            n_estimators=300, max_depth=6, min_samples_leaf=15,
            random_state=42, n_jobs=-1,
        ),
    }


def run(rows):
    # build_examples sorts neither input nor matches: sort first, including
    # deterministic same-day tie breaking, and never use the outcome of a
    # later match to construct an earlier match's features.
    rows = sorted(rows, key=lambda r: (str(r["date"]), r.get("source_file", ""), r["home"], r["away"]))
    x, y, meta, _ = build_examples(rows)
    n = len(y)
    a, b = int(.65*n), int(.80*n)
    if a < 100 or b-a < 40 or n-b < 40:
        raise ValueError(f"Not enough historical examples for chronological splits: {n}")
    trial_results = {}
    for name, factory in candidates().items():
        model = factory()
        model.fit(x[:a], y[:a])
        trial_results[name] = metrics(y[a:b], model.predict_proba(x[a:b]), list(model.classes_))
    selected = min(trial_results, key=lambda name: trial_results[name]["log_loss"])
    # Holdout is used exactly once after model selection.
    model = candidates()[selected]()
    model.fit(x[:b], y[:b])
    test = metrics(y[b:], model.predict_proba(x[b:]), list(model.classes_))
    # Baselines use only pre-holdout outcome frequencies.
    frequencies = np.array([(y[:b] == cls).mean() for cls in CLASSES])
    baseline = metrics(y[b:], np.tile(frequencies, (n-b, 1)), CLASSES)
    return {
        "experiment": "europe-offline-candidate-v1",
        "scope": "Champions League, Europa League, Conference League and qualifiers in input",
        "train_rows": a, "validation_rows": b-a, "test_rows": n-b,
        "validation_first_match": meta[a], "test_first_match": meta[b],
        "test_last_match": meta[-1],
        "validation_candidates": trial_results,
        "selected_model": selected,
        "test_candidate": test,
        "test_frequency_baseline": baseline,
        "note": "Research only; does not modify production models. Compare against production on identical holdout before promotion.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows-json", required=True, type=Path, help="Locally saved JSON array of parsed historical matches")
    parser.add_argument("--output", type=Path, default=Path("app/ml/artifacts/europe_offline_candidate_v1.json"))
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
