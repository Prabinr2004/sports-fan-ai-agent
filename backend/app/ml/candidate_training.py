from __future__ import annotations

"""Train research-only league-specific Understat candidate artifacts.

Candidates are deliberately stored with a candidate prefix and are never loaded
by trained.py's production path. Current 2026/27 completed matches update team
state but are not fit rows, preserving the forward-validation boundary.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.metrics import accuracy_score, log_loss

from app.ml.league_policy import candidate_for_league
from app.ml.understat_forward_2026 import select_historical_model
from app.ml.understat_xg_benchmark import (
    ADVANCED_FEATURES,
    BASE_FEATURES,
    CURRENT_SEASON,
    LEAGUES,
    XG_FEATURES,
    build_examples,
    download_league,
    make_model,
    multiclass_brier,
)

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
FAMILY_FEATURES = {
    "results_only": BASE_FEATURES,
    "rolling_xg": XG_FEATURES,
    "understat_team_stats": ADVANCED_FEATURES,
}


def train_candidate(key: str, out: Path = ARTIFACT_DIR):
    policy = candidate_for_league(key)
    if policy.status != "observe":
        return {
            "league": LEAGUES[key]["name"],
            "status": "skipped",
            "reason": policy.reason,
            "production_changed": False,
        }

    rows = download_league(key, include_current=True)
    historical = [r for r in rows if r["season"] != CURRENT_SEASON]

    xb, xx, xa, y, meta, _ = build_examples(historical)
    matrices = {
        "results_only": xb,
        "rolling_xg": xx,
        "understat_team_stats": xa,
    }
    family = policy.feature_family
    x = matrices[family]
    selection = select_historical_model(x, y)
    c = float(selection["selected_C"])

    # Research diagnostic only: final historical 20%. The artifact itself is
    # refit on all historical rows after C is selected.
    split = int(len(y) * 0.80)
    diagnostic = make_model(c)
    diagnostic.fit(x[:split], y[:split])
    probs = diagnostic.predict_proba(x[split:])
    pred = diagnostic.predict(x[split:])

    model = make_model(c)
    model.fit(x, y)

    # Build state through current completed matches for future fixture inference.
    _, _, _, _, _, current_state = build_examples(rows)
    feature_names = FAMILY_FEATURES[family]
    version = f"{key}-understat-candidate-v1"
    bundle = {
        "model": model,
        "classes": list(model.classes_),
        "feature_names": feature_names,
        "team_states": current_state,
        "league_key": key,
        "league_name": LEAGUES[key]["name"],
        "model_version": version,
        "feature_family": family,
        "candidate_only": True,
        "production_approved": False,
        "historical_through_season": "2025/26",
        "state_through_season": "2026/27-current",
    }

    out.mkdir(parents=True, exist_ok=True)
    artifact = out / f"candidate_{key}_understat_v1.joblib"
    metrics_path = out / f"candidate_{key}_understat_v1_metrics.json"
    joblib.dump(bundle, artifact)

    metrics = {
        "league": LEAGUES[key]["name"],
        "model_version": version,
        "feature_family": family,
        "selected_C": c,
        "selection_validation_log_loss": selection["validation_log_loss"],
        "historical_rows": len(y),
        "diagnostic_rows": len(y) - split,
        "diagnostic_accuracy": float(accuracy_score(y[split:], pred)),
        "diagnostic_log_loss": float(log_loss(y[split:], probs, labels=diagnostic.classes_)),
        "diagnostic_brier": multiclass_brier(y[split:], probs, diagnostic.classes_),
        "feature_names": feature_names,
        "current_team_states": len(current_state),
        "candidate_only": True,
        "production_changed": False,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "last_historical_feature_match": meta[-1],
    }
    metrics_path.write_text(json.dumps(metrics, indent=2))
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Train research-only Understat candidates")
    parser.add_argument("--league", choices=[*LEAGUES.keys(), "all"], default="all")
    args = parser.parse_args()
    keys = list(LEAGUES) if args.league == "all" else [args.league]
    result = {key: train_candidate(key) for key in keys}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
