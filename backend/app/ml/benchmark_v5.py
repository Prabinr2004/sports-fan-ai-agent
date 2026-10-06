from __future__ import annotations

"""Benchmark richer v5 features without changing FanSphere production models."""

import json
from datetime import datetime, timezone
from pathlib import Path

from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.features_v5 import FEATURE_NAMES_V5, build_examples_v5
from app.ml.training import LEAGUES, brier, download_rows


def candidates():
    return {
        "logistic": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=3000, C=0.05)),
        ]),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            learning_rate=0.035, max_iter=220, max_leaf_nodes=9,
            min_samples_leaf=28, l2_regularization=2.0, random_state=42,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=600, max_depth=7, min_samples_leaf=10,
            max_features=0.65, class_weight="balanced_subsample",
            random_state=42, n_jobs=-1,
        ),
    }


def score(model, x1, y1, x2, y2):
    model.fit(x1, y1)
    probs = model.predict_proba(x2); pred = model.predict(x2); classes = list(model.classes_)
    return {
        "accuracy": float(accuracy_score(y2, pred)),
        "log_loss": float(log_loss(y2, probs, labels=classes)),
        "brier": brier(y2, probs, classes),
    }


def run_league(key: str):
    x, y, meta, states = build_examples_v5(download_rows(key))
    train_end, val_end = int(len(y) * .70), int(len(y) * .80)
    trials = {}
    for name, model in candidates().items():
        trials[name] = score(model, x[:train_end], y[:train_end], x[train_end:val_end], y[train_end:val_end])
    selected_name = min(trials, key=lambda n: trials[n]["log_loss"])
    selected = candidates()[selected_name]
    test = score(selected, x[:val_end], y[:val_end], x[val_end:], y[val_end:])
    return {
        "league": LEAGUES[key]["name"], "experiment": "v5-richer-features",
        "rows_total": len(y), "train_rows": train_end, "validation_rows": val_end-train_end,
        "test_rows": len(y)-val_end, "features": FEATURE_NAMES_V5,
        "candidate_trials": trials, "selected_model": selected_name,
        "test_accuracy": test["accuracy"], "test_log_loss": test["log_loss"], "test_brier": test["brier"],
        "chronological_train_validation_test": True,
        "validation_first_match": meta[train_end], "test_first_match": meta[val_end], "test_last_match": meta[-1],
        "team_states": len(states), "trained_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "Experimental only. Production remains explicitly pinned to v2."
    }


def run_all(out: Path):
    result = {}
    for key in LEAGUES:
        try: result[key] = run_league(key)
        except Exception as exc: result[key] = {"league": LEAGUES[key]["name"], "error": str(exc)}
    out.mkdir(parents=True, exist_ok=True)
    (out / "v5_benchmark.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    print(json.dumps(run_all(Path(__file__).resolve().parent / "artifacts"), indent=2))
