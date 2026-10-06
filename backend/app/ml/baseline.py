from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TeamForm:
    matches: int
    points_per_game: float
    goals_for_per_game: float
    goals_against_per_game: float


def form_from_matches(matches: Iterable[dict], team_id: str, limit: int = 8) -> TeamForm:
    """Build pre-match form features from completed matches only."""
    finished = [m for m in matches if m.get("status") == "FINISHED"][-limit:]
    points = goals_for = goals_against = 0.0
    used = 0
    for match in finished:
        home = str((match.get("home_team") or {}).get("id"))
        away = str((match.get("away_team") or {}).get("id"))
        score = match.get("score") or {}
        hg, ag = score.get("home"), score.get("away")
        if hg is None or ag is None or team_id not in {home, away}:
            continue
        used += 1
        gf, ga = (hg, ag) if team_id == home else (ag, hg)
        goals_for += gf
        goals_against += ga
        if gf > ga:
            points += 3
        elif gf == ga:
            points += 1
    if not used:
        return TeamForm(0, 1.35, 1.35, 1.35)
    return TeamForm(used, points / used, goals_for / used, goals_against / used)


def _softmax(values: list[float]) -> list[float]:
    peak = max(values)
    exp = [math.exp(v - peak) for v in values]
    total = sum(exp)
    return [v / total for v in exp]


def baseline_probabilities(home: TeamForm, away: TeamForm) -> dict:
    """Transparent heuristic baseline.

    This is intentionally labelled a baseline, not a trained ML model. It gives
    FanSphere a deterministic probability contract while the historical training
    pipeline is built and evaluated.
    """
    home_strength = 0.75 * home.points_per_game + 0.35 * home.goals_for_per_game - 0.25 * home.goals_against_per_game
    away_strength = 0.75 * away.points_per_game + 0.35 * away.goals_for_per_game - 0.25 * away.goals_against_per_game
    delta = home_strength - away_strength
    home_logit = 0.28 + delta
    draw_logit = 0.35 - abs(delta) * 0.45
    away_logit = -0.05 - delta
    home_p, draw_p, away_p = _softmax([home_logit, draw_logit, away_logit])
    probs = {"HOME": home_p, "DRAW": draw_p, "AWAY": away_p}
    pick = max(probs, key=probs.get)
    return {
        "pick": pick,
        "probabilities": {key: round(value, 4) for key, value in probs.items()},
        "model_version": "form-baseline-v1",
        "model_type": "heuristic-baseline",
        "features": {
            "home_points_per_game": round(home.points_per_game, 3),
            "away_points_per_game": round(away.points_per_game, 3),
            "home_goals_for_per_game": round(home.goals_for_per_game, 3),
            "away_goals_for_per_game": round(away.goals_for_per_game, 3),
            "home_goals_against_per_game": round(home.goals_against_per_game, 3),
            "away_goals_against_per_game": round(away.goals_against_per_game, 3),
        },
        "training_status": "baseline-not-trained",
    }
