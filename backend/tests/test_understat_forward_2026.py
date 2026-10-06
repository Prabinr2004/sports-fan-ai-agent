import numpy as np

from app.ml.understat_forward_2026 import select_historical_model
from app.ml.understat_xg_benchmark import make_model


def test_historical_model_selection_returns_valid_choice():
    # Three separable classes repeated through time; selection should complete
    # using only the supplied historical matrix/labels.
    x = np.asarray([
        [0.0, 0.0], [1.0, 0.0], [0.0, 1.0],
        [0.1, 0.0], [1.1, 0.0], [0.0, 1.1],
    ] * 30, dtype=float)
    y = np.asarray(["DRAW", "HOME", "AWAY", "DRAW", "HOME", "AWAY"] * 30)

    result = select_historical_model(x, y)

    assert result["selected_C"] is not None
    assert result["validation_log_loss"] >= 0
    assert result["historical_train_rows"] + result["historical_validation_rows"] == len(y)


def test_make_model_accepts_selected_c():
    model = make_model(0.05)
    assert model is not None
