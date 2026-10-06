from __future__ import annotations

"""Forward validation on completed 2026/27 Big Five matches.

Historical validation selects the feature family (results-only, rolling xG, or
richer Understat stats) and regularization strength. The chosen model is then
refit on all 2022/23-2025/26 feature rows and evaluated only on completed
2026/27 matches. No production artifacts are written.
"""

import argparse
import json
from typing import Any

import numpy as np
from sklearn.metrics import accuracy_score, log_loss

from app.ml.understat_xg_benchmark import (
    C_VALUES,
    CURRENT_SEASON,
    LEAGUES,
    build_examples,
    calibration_summary,
    download_league,
    make_model,
    multiclass_brier,
)

VARIANTS = ("results_only", "rolling_xg", "understat_team_stats")


def split_forward_examples(key: str):
    rows = download_league(key, include_current=True)
    xb, xx, xa, y, meta, _ = build_examples(rows)
    current_mask = np.asarray([m["season"] == CURRENT_SEASON for m in meta], dtype=bool)
    historical_mask = ~current_mask
    if not current_mask.any():
        raise RuntimeError(f"No completed 2026/27 feature rows for {LEAGUES[key]['name']}")
    matrices = {
        "results_only": xb,
        "rolling_xg": xx,
        "understat_team_stats": xa,
    }
    return matrices, y, meta, historical_mask, current_mask


def select_historical_model(x: np.ndarray, y: np.ndarray):
    n = len(y)
    train_end = int(n * 0.80)
    if train_end < 100 or train_end >= n:
        raise RuntimeError(f"Not enough historical rows: {n}")

    best_c = None
    best_loss = float("inf")
    trials = []
    for c in C_VALUES:
        model = make_model(c)
        model.fit(x[:train_end], y[:train_end])
        probs = model.predict_proba(x[train_end:])
        loss = float(log_loss(y[train_end:], probs, labels=model.classes_))
        trials.append({"C": c, "validation_log_loss": loss})
        if loss < best_loss:
            best_c, best_loss = c, loss

    return {
        "selected_C": best_c,
        "validation_log_loss": best_loss,
        "candidate_trials": trials,
        "historical_train_rows": train_end,
        "historical_validation_rows": n - train_end,
    }


def evaluate_current(x_hist, y_hist, x_current, y_current, c: float) -> dict[str, Any]:
    model = make_model(c)
    model.fit(x_hist, y_hist)
    probs = model.predict_proba(x_current)
    pred = model.predict(x_current)
    return {
        "test_accuracy": float(accuracy_score(y_current, pred)),
        "test_log_loss": float(log_loss(y_current, probs, labels=model.classes_)),
        "test_brier": multiclass_brier(y_current, probs, model.classes_),
        "calibration": calibration_summary(y_current, probs, model.classes_),
    }


def benchmark_league(key: str) -> dict[str, Any]:
    matrices, y, meta, historical_mask, current_mask = split_forward_examples(key)
    y_hist = y[historical_mask]
    y_current = y[current_mask]
    hist_meta = [m for m, keep in zip(meta, historical_mask) if keep]
    current_meta = [m for m, keep in zip(meta, current_mask) if keep]

    variant_results = {}
    for name, matrix in matrices.items():
        x_hist = matrix[historical_mask]
        x_current = matrix[current_mask]
        selection = select_historical_model(x_hist, y_hist)
        current = evaluate_current(
            x_hist, y_hist, x_current, y_current, float(selection["selected_C"])
        )
        variant_results[name] = {**selection, **current}

    selected_variant = min(
        VARIANTS,
        key=lambda name: variant_results[name]["validation_log_loss"],
    )
    selected = variant_results[selected_variant]

    return {
        "league": LEAGUES[key]["name"],
        "selection_rule": "lowest historical validation log loss only",
        "selected_variant": selected_variant,
        "selected_C": selected["selected_C"],
        "historical_feature_rows": int(historical_mask.sum()),
        "current_2026_27_test_rows": int(current_mask.sum()),
        "historical_last_feature_match": hist_meta[-1],
        "current_first_feature_match": current_meta[0],
        "current_last_feature_match": current_meta[-1],
        "variants": variant_results,
        "selected_current_accuracy": selected["test_accuracy"],
        "selected_current_log_loss": selected["test_log_loss"],
        "selected_current_brier": selected["test_brier"],
        "production_changed": False,
    }


def main():
    parser = argparse.ArgumentParser(description="Forward 2026/27 Understat validation")
    parser.add_argument("--league", choices=[*LEAGUES.keys(), "all"], default="all")
    args = parser.parse_args()
    selected = list(LEAGUES) if args.league == "all" else [args.league]

    results = {
        "source": "Understat current JSON endpoints",
        "method": (
            "historical validation selects feature family + C; refit on all "
            "2022/23-2025/26 feature rows; test only completed 2026/27 matches"
        ),
        "requested_league": args.league,
        "production_changed": False,
        "leagues": {},
    }

    for key in selected:
        try:
            results["leagues"][key] = benchmark_league(key)
        except Exception as exc:
            results["leagues"][key] = {
                "league": LEAGUES[key]["name"],
                "error": str(exc),
                "production_changed": False,
            }

    successful = [r for r in results["leagues"].values() if "error" not in r]
    results["selected_variant_counts"] = {
        variant: sum(r["selected_variant"] == variant for r in successful)
        for variant in VARIANTS
    }
    results["promotion_rule"] = (
        "Still research-only. Consider production integration only if the "
        "historically selected feature family shows acceptable forward 2026/27 "
        "probability quality across multiple leagues and survives a production "
        "trainer/runtime implementation review."
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
