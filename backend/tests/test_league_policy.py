from app.ml.league_policy import (
    candidate_for_league,
    eligible_for_candidate_review,
)


def test_production_baseline_leagues_cannot_auto_qualify():
    assert candidate_for_league("epl").feature_family == "results_only"
    assert candidate_for_league("seriea").feature_family == "results_only"
    assert not eligible_for_candidate_review(
        "seriea",
        forward_matches=200,
        candidate_log_loss=0.80,
        baseline_log_loss=0.90,
        candidate_brier=0.48,
        baseline_brier=0.52,
    )


def test_observe_candidate_requires_enough_forward_matches():
    assert candidate_for_league("bundesliga").feature_family == "understat_team_stats"
    assert not eligible_for_candidate_review(
        "bundesliga",
        forward_matches=30,
        candidate_log_loss=0.90,
        baseline_log_loss=0.94,
        candidate_brier=0.53,
        baseline_brier=0.56,
    )


def test_observe_candidate_requires_both_probability_metrics_to_improve():
    assert eligible_for_candidate_review(
        "bundesliga",
        forward_matches=80,
        candidate_log_loss=0.90,
        baseline_log_loss=0.94,
        candidate_brier=0.53,
        baseline_brier=0.56,
    )
    assert not eligible_for_candidate_review(
        "bundesliga",
        forward_matches=80,
        candidate_log_loss=0.90,
        baseline_log_loss=0.94,
        candidate_brier=0.57,
        baseline_brier=0.56,
    )
