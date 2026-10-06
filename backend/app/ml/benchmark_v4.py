from __future__ import annotations

"""FanSphere domestic v4 experiment.

This file is deliberately benchmark-only: it never changes the production model.
It compares multiple sklearn classifiers on the same chronological holdout and
writes metrics so a model is promoted only after evidence supports it.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.training import LEAGUES, brier, build_examples, download_rows


def _models():
    return {
        "logistic": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=3000, C=0.05)),
        ]),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=250,
            max_leaf_nodes=15,
            min_samples_leaf=20,
            l2_regularization=1.0,
            random_state=42,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=500,
            max_depth=8,
            min_samples_leaf=8,
            max_features="sqrt",
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=500,
            max_depth=9,
            min_samples_leaf=6,
            max_features="sqrt",
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
    }


def _evaluate(model, x_train, y_train, x_test, y_test):
    model.fit(x_train, y_train)
    probs = model.predict_proba(x_test)
    pred = model.predict(x_test)
    classes = list(model.classes_)
    return {
        "accuracy": float(accuracy_score(y_test, pred)),
        "log_loss": float(log_loss(y_test, probs, labels=classes)),
        "brier": brier(y_test, probs, classes),
    }


def benchmark_league(key: str, out: Path):
    x, y, meta, states = build_examples(download_rows(key))
    n = len(y)
    train_end = int(n * 0.70)
    val_end = int(n * 0.80)
    if train_end < 100 or val_end >= n:
        raise RuntimeError("Not enough completed matches")

    trials = {}
    fitted = {}
    for name, model in _models().items():
        metrics = _evaluate(model, x[:train_end], y[:train_end], x[train_end:val_end], y[train_end:val_end])
        trials[name] = metrics
        fitted[name] = model

    # Probability quality chooses the candidate; accuracy remains visible.
    selected_name = min(trials, key=lambda name: trials[name]["log_loss"])
    selected = _models()[selected_name]
    selected.fit(x[:val_end], y[:val_end])
    test_probs = selected.predict_proba(x[val_end:])
    test_pred = selected.predict(x[val_end:])
    classes = list(selected.classes_)

    cfg = LEAGUES[key]
    result = {
        "league": cfg["name"],
        "experiment": "v4-model-bakeoff",
        "rows_total": n,
        "train_rows": train_end,
        "validation_rows": val_end - train_end,
        "refit_rows": val_end,
        "test_rows": n - val_end,
        "selection_metric": "validation_log_loss",
        "candidate_trials": trials,
        "selected_model": selected_name,
        "test_accuracy": float(accuracy_score(y[val_end:], test_pred)),
        "test_log_loss": float(log_loss(y[val_end:], test_probs, labels=classes)),
        "test_brier": brier(y[val_end:], test_probs, classes),
        "chronological_train_validation_test": True,
        "validation_first_match": meta[train_end],
        "test_first_match": meta[val_end],
        "test_last_match": meta[-1],
        "team_states": len(states),
        "trained_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "Experimental only; production selection is unchanged.",
    }

    out.mkdir(parents=True, exist_ok=True)
    (out / f"{key}_v4_benchmark.json").write_text(json.dumps(result, indent=2))
    # Save selected experiment separately; runtime does not auto-load it.
    joblib.dump({
        "model": selected,
        "classes": classes,
        "team_states": states,
        "league_key": key,
        "league_name": cfg["name"],
        "model_version": f"{key}-experimental-v4-{selected_name}",
    }, out / f"{key}_experimental_v4.joblib")
    return result


def run_all(out: Path):
    results = {}
    for key in LEAGUES:
        try:
            results[key] = benchmark_league(key, out)
        except Exception as exc:
            results[key] = {"league": LEAGUES[key]["name"], "error": str(exc)}
    return results


if __name__ == "__main__":
    output = Path(__file__).resolve().parent / "artifacts"
    print(json.dumps(run_all(output), indent=2))
