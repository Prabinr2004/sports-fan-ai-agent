from __future__ import annotations

"""League-specific research policy for FanSphere domestic prediction models.

This module records evidence gates and candidate feature-family decisions. It
does NOT alter trained.py's PRODUCTION_MODEL_VERSION mapping and therefore
cannot promote an experimental model by itself.
"""

from dataclasses import dataclass

SUPPORTED_LEAGUES = ("epl", "laliga", "bundesliga", "seriea", "ligue1")
FEATURE_FAMILIES = ("results_only", "rolling_xg", "understat_team_stats")


@dataclass(frozen=True)
class CandidatePolicy:
    feature_family: str
    status: str
    reason: str
    min_forward_matches: int = 75


# Based on historical selection + the first 2026/27 forward-validation checkpoint.
# "observe" means collect more forward matches before considering implementation.
CANDIDATE_POLICY = {
    "epl": CandidatePolicy(
        "results_only", "keep_baseline",
        "Richer Understat features did not establish a reliable forward advantage.",
    ),
    "laliga": CandidatePolicy(
        "understat_team_stats", "observe",
        "Historical validation preferred richer stats, but the current-season forward "
        "sample did not beat the simpler results-only variant.",
    ),
    "bundesliga": CandidatePolicy(
        "understat_team_stats", "observe",
        "Strongest current richer-feature candidate; require a larger forward sample "
        "before production integration.",
    ),
    "seriea": CandidatePolicy(
        "results_only", "keep_baseline",
        "Historical validation and forward evaluation favor the simpler family.",
    ),
    "ligue1": CandidatePolicy(
        "results_only", "keep_baseline",
        "Richer historical selection failed to generalize in the early 2026/27 holdout.",
    ),
}


def candidate_for_league(key: str) -> CandidatePolicy:
    if key not in CANDIDATE_POLICY:
        raise KeyError(f"Unsupported league: {key}")
    return CANDIDATE_POLICY[key]


def eligible_for_candidate_review(
    key: str,
    *,
    forward_matches: int,
    candidate_log_loss: float,
    baseline_log_loss: float,
    candidate_brier: float,
    baseline_brier: float,
) -> bool:
    policy = candidate_for_league(key)
    if policy.status != "observe":
        return False
    if forward_matches < policy.min_forward_matches:
        return False
    return (
        candidate_log_loss < baseline_log_loss
        and candidate_brier < baseline_brier
    )
