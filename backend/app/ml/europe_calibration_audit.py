"""Offline European probability calibration audit; no production changes.

Fits base model on earliest 65%, temperature on next 15%, reports
later 20% as a retrospective diagnostic (already inspected in prior
experiments; NOT a fresh untouched holdout).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.europe_training import build_examples
from app.ml.europe_offline_benchmark import metrics


def temperature_scale(probs, temperature):
    logits = np.log(np.clip(probs, 1e-12, 1.0)) / temperature
    logits -= logits.max(axis=1, keepdims=True)
    e = np.exp(logits)
    return e / e.sum(axis=1, keepdims=True)


def draw_bins(y, probs, classes):
    idx = list(classes).index("DRAW")
    p = probs[:, idx]
    result = []
    for low, high in [(0, .15), (.15, .25), (.25, .35), (.35, 1.01)]:
        mask = (p >= low) & (p < high)
        result.append({
            "probability_range": [low, min(high, 1.)],
            "matches": int(mask.sum()),
            "mean_predicted_draw_probability": float(p[mask].mean()) if mask.any() else None,
            "actual_draw_rate": float((y[mask] == "DRAW").mean()) if mask.any() else None,
        })
    return result


def run(rows):
    rows = sorted(rows, key=lambda r: (str(r["date"]), r.get("source_file", ""), r["home"], r["away"]))
    x, y, meta, _ = build_examples(rows)
    a, b = int(.65 * len(y)), int(.80 * len(y))
    if a < 100 or b-a < 40 or len(y)-b < 40:
        raise ValueError("Insufficient chronological data")
    model = make_pipeline(StandardScaler(), LogisticRegression(C=.25, max_iter=2500))
    model.fit(x[:a], y[:a])
    classes = list(model.classes_)
    calibration_probs = model.predict_proba(x[a:b])
    true_indices = np.array([classes.index(label) for label in y[a:b]])
    def objective(t):
        scaled = temperature_scale(calibration_probs, t)
        return float(-np.log(np.clip(scaled[np.arange(len(true_indices)), true_indices], 1e-12, 1)).mean())
    fitted = minimize_scalar(objective, bounds=(.5, 3.), method="bounded")
    raw = model.predict_proba(x[b:])
    adjusted = temperature_scale(raw, float(fitted.x))
    return {
        "experiment": "europe-calibration-audit-v1",
        "model_fit_rows": a,
        "calibration_rows": b-a,
        "retrospective_test_rows": len(y)-b,
        "test_first_match": meta[b],
        "test_last_match": meta[-1],
        "selected_temperature": float(fitted.x),
        "raw": metrics(y[b:], raw, classes),
        "temperature_scaled": metrics(y[b:], adjusted, classes),
        "raw_draw_bins": draw_bins(y[b:], raw, classes),
        "scaled_draw_bins": draw_bins(y[b:], adjusted, classes),
        "warning": "This later test period was previously inspected. Findings are exploratory, not independent deployment evidence. A future chronological holdout is required.",
        "production_changes": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rows-json", required=True, type=Path)
    p.add_argument("--output", type=Path, default=Path("app/ml/artifacts/europe_calibration_audit.json"))
    args = p.parse_args()
    rows = json.loads(args.rows_json.read_text())
    for row in rows:
        if isinstance(row.get("date"), str):
            row["date"] = datetime.fromisoformat(row["date"])
    result = run(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
