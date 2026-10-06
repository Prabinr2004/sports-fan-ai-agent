import numpy as np

from app.ml import candidates
from app.ml.candidates import _candidate_feature_row


def _state(seed: float):
    return {
        "ppg_5": 1.2 + seed, "ppg_10": 1.3 + seed,
        "home_ppg_5": 1.4 + seed, "away_ppg_5": 1.1 + seed,
        "gf_5": 1.5 + seed, "ga_5": 1.0 + seed, "gd_10": 0.3 + seed,
        "elo": 1500 + seed * 100,
        "xgf_5": 1.6 + seed, "xga_5": 1.1 + seed, "xgd_10": 0.4 + seed,
        "npxgf_5": 1.4 + seed, "npxga_5": 1.0 + seed,
        "xpts_5": 1.5 + seed, "ppda_5": 9.0 + seed, "deep_5": 6.0 + seed,
    }


def test_candidate_feature_row_respects_requested_order():
    home, away = _state(0.2), _state(0.0)
    names = ["home_elo", "away_elo", "elo_diff", "home_xpts_5", "away_ppda_5"]
    row = _candidate_feature_row(home, away, names)
    assert row.shape == (1, len(names))
    assert np.isclose(row[0, 0], home["elo"])
    assert np.isclose(row[0, 1], away["elo"])
    assert np.isclose(row[0, 2], home["elo"] - away["elo"])
    assert np.isclose(row[0, 3], home["xpts_5"])
    assert np.isclose(row[0, 4], away["ppda_5"])


def test_comparison_keeps_candidate_separate_from_production(monkeypatch):
    production = {"model_version": "bundesliga-logreg-v2", "pick": "HOME"}
    candidate = {"model_version": "bundesliga-understat-candidate-v1", "pick": "DRAW"}
    monkeypatch.setattr(candidates, "predict_from_team_names", lambda *args: production)
    monkeypatch.setattr(candidates, "predict_candidate", lambda *args: candidate)

    result = candidates.compare_with_production(
        "bundesliga", "Bayern Munich", "Borussia Dortmund", "Bundesliga"
    )
    assert result["production"] is production
    assert result["candidate"] is candidate
    assert result["production_changed"] is False
