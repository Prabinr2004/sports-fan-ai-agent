from __future__ import annotations

"""Read-only helpers for inspecting experimental domestic ML candidates."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


@lru_cache(maxsize=5)
def load_candidate_bundle(key: str) -> dict[str, Any] | None:
    path = ARTIFACT_DIR / f"candidate_{key}_understat_v1.joblib"
    if not path.exists():
        return None
    bundle = joblib.load(path)
    if not bundle.get("candidate_only"):
        return None
    if bundle.get("production_approved") is not False:
        return None
    return bundle


def candidate_summary(key: str) -> dict[str, Any] | None:
    bundle = load_candidate_bundle(key)
    if bundle is None:
        return None
    return {
        "league_key": bundle.get("league_key"),
        "league_name": bundle.get("league_name"),
        "model_version": bundle.get("model_version"),
        "feature_family": bundle.get("feature_family"),
        "candidate_only": bundle.get("candidate_only"),
        "production_approved": bundle.get("production_approved"),
        "historical_through_season": bundle.get("historical_through_season"),
        "state_through_season": bundle.get("state_through_season"),
        "team_states": len(bundle.get("team_states") or {}),
    }


def _candidate_feature_row(home: dict[str, Any], away: dict[str, Any], names: list[str]):
    values = {
        "home_ppg_5": home["ppg_5"], "away_ppg_5": away["ppg_5"],
        "home_ppg_10": home["ppg_10"], "away_ppg_10": away["ppg_10"],
        "home_venue_ppg_5": home["home_ppg_5"], "away_venue_ppg_5": away["away_ppg_5"],
        "home_gf_5": home["gf_5"], "away_gf_5": away["gf_5"],
        "home_ga_5": home["ga_5"], "away_ga_5": away["ga_5"],
        "home_gd_10": home["gd_10"], "away_gd_10": away["gd_10"],
        "home_elo": home["elo"], "away_elo": away["elo"], "elo_diff": home["elo"] - away["elo"],
        "home_xgf_5": home["xgf_5"], "away_xgf_5": away["xgf_5"],
        "home_xga_5": home["xga_5"], "away_xga_5": away["xga_5"],
        "home_xgd_10": home["xgd_10"], "away_xgd_10": away["xgd_10"],
        "home_npxgf_5": home["npxgf_5"], "away_npxgf_5": away["npxgf_5"],
        "home_npxga_5": home["npxga_5"], "away_npxga_5": away["npxga_5"],
        "home_xpts_5": home["xpts_5"], "away_xpts_5": away["xpts_5"],
        "home_ppda_5": home["ppda_5"], "away_ppda_5": away["ppda_5"],
        "home_deep_5": home["deep_5"], "away_deep_5": away["deep_5"],
    }
    return np.asarray([[values[name] for name in names]], dtype=float)


def _find_candidate_state(states: dict[str, Any], name: str):
    wanted = name.casefold().strip()
    for team_name, state in states.items():
        if team_name.casefold().strip() == wanted:
            return state
    return None


def predict_candidate(key: str, home_name: str, away_name: str) -> dict[str, Any] | None:
    """Research-only prediction. Never used by the normal production endpoint."""
    bundle = load_candidate_bundle(key)
    if bundle is None:
        return None
    states = bundle.get("team_states") or {}
    home = _find_candidate_state(states, home_name)
    away = _find_candidate_state(states, away_name)
    if home is None or away is None:
        return None
    names = list(bundle["feature_names"])
    features = _candidate_feature_row(home, away, names)
    model = bundle["model"]
    raw = model.predict_proba(features)[0]
    classes = list(getattr(model, "classes_", bundle.get("classes", [])))
    probs = {str(label): float(raw[i]) for i, label in enumerate(classes)}
    return {
        "probabilities": {label: probs.get(label, 0.0) for label in ("HOME", "DRAW", "AWAY")},
        "pick": max(probs, key=probs.get),
        "model_version": bundle["model_version"],
        "feature_family": bundle["feature_family"],
        "candidate_only": True,
        "production_approved": False,
    }


def compare_with_production(
    key: str, home_name: str, away_name: str, competition: str
) -> dict[str, Any]:
    """Side-by-side research comparison without changing production selection."""
    production = predict_from_team_names(home_name, away_name, competition)
    candidate = predict_candidate(key, home_name, away_name)
    return {
        "home": home_name,
        "away": away_name,
        "league_key": key,
        "production": production,
        "candidate": candidate,
        "production_changed": False,
    }
