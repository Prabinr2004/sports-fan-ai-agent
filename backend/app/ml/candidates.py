from __future__ import annotations

"""Read-only helpers for inspecting experimental domestic ML candidates."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

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
