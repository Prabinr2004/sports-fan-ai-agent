from app.ml.candidate_training import FAMILY_FEATURES
from app.ml.league_policy import candidate_for_league
from app.ml.trained import PRODUCTION_MODEL_VERSION


def test_candidate_feature_families_match_policy():
    assert candidate_for_league("bundesliga").feature_family in FAMILY_FEATURES
    assert candidate_for_league("laliga").feature_family in FAMILY_FEATURES


def test_candidate_work_does_not_change_production_versions():
    assert PRODUCTION_MODEL_VERSION == {
        "epl": "v2",
        "laliga": "v2",
        "bundesliga": "v2",
        "seriea": "v2",
        "ligue1": "v2",
    }


def test_candidate_policy_only_trains_observe_leagues():
    assert candidate_for_league("bundesliga").status == "observe"
    assert candidate_for_league("laliga").status == "observe"
    assert candidate_for_league("epl").status == "keep_baseline"
    assert candidate_for_league("seriea").status == "keep_baseline"
    assert candidate_for_league("ligue1").status == "keep_baseline"
