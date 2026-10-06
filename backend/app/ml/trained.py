from __future__ import annotations

from collections import deque
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.ml.baseline import form_from_matches

ARTIFACT = Path(__file__).resolve().parent / "artifacts" / "epl_logreg_v1.joblib"


@lru_cache(maxsize=1)
def load_model_bundle() -> dict[str, Any] | None:
    if not ARTIFACT.exists():
        return None
    return joblib.load(ARTIFACT)


def _estimate_live_elo(form: Any) -> float:
    # Runtime provider data does not contain the historical Elo state used during
    # training yet. Map recent points-per-game to a conservative Elo estimate.
    # This keeps the trained model usable while making the approximation explicit.
    return 1500.0 + (float(form.points_per_game) - 1.35) * 90.0


def predict_from_recent_results(home_results: list[dict], away_results: list[dict], home_id: str, away_id: str) -> dict[str, Any] | None:
    bundle = load_model_bundle()
    if bundle is None:
        return None

    home = form_from_matches(home_results, home_id, limit=5)
    away = form_from_matches(away_results, away_id, limit=5)
    home_elo = _estimate_live_elo(home)
    away_elo = _estimate_live_elo(away)
    features = np.asarray([[
        home.points_per_game,
        away.points_per_game,
        home.goals_for_per_game,
        away.goals_for_per_game,
        home.goals_against_per_game,
        away.goals_against_per_game,
        home_elo,
        away_elo,
        home_elo - away_elo,
    ]], dtype=float)

    model = bundle["model"]
    probabilities = model.predict_proba(features)[0]
    classes = list(getattr(model, "classes_", bundle.get("classes", [])))
    probs = {str(label): float(probabilities[i]) for i, label in enumerate(classes)}
    pick = max(probs, key=probs.get)
    return {
        "probabilities": {"HOME": probs.get("HOME", 0.0), "DRAW": probs.get("DRAW", 0.0), "AWAY": probs.get("AWAY", 0.0)},
        "pick": pick,
        "model_version": "epl-logreg-v1",
        "model_type": "scaled-multinomial-logistic-regression",
        "training_status": "trained",
        "runtime_elo_status": "estimated-from-recent-form",
        "features": {
            "home_ppg_5": home.points_per_game,
            "away_ppg_5": away.points_per_game,
            "home_gf_5": home.goals_for_per_game,
            "away_gf_5": away.goals_for_per_game,
            "home_ga_5": home.goals_against_per_game,
            "away_ga_5": away.goals_against_per_game,
            "home_elo": home_elo,
            "away_elo": away_elo,
            "elo_diff": home_elo - away_elo,
        },
    }
