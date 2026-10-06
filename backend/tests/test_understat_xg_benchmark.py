from app.ml.understat_xg_benchmark import (
    BASE_FEATURES,
    XG_FEATURES,
    build_examples,
)


def _rows():
    rows = []
    teams = ["Alpha", "Beta", "Gamma", "Delta"]
    day = 1
    # Every team accumulates enough prior history before the later rows.
    pairings = [
        ("Alpha", "Beta"), ("Gamma", "Delta"),
        ("Beta", "Gamma"), ("Delta", "Alpha"),
        ("Alpha", "Gamma"), ("Beta", "Delta"),
        ("Gamma", "Alpha"), ("Delta", "Beta"),
        ("Alpha", "Beta"), ("Gamma", "Delta"),
        ("Beta", "Gamma"), ("Delta", "Alpha"),
        ("Alpha", "Gamma"), ("Beta", "Delta"),
        ("Gamma", "Alpha"), ("Delta", "Beta"),
    ]
    for i, (home, away) in enumerate(pairings):
        hg = (i + 1) % 3
        ag = i % 2
        rows.append(
            {
                "date": f"2025-01-{day:02d} 15:00:00",
                "home": home,
                "away": away,
                "hg": hg,
                "ag": ag,
                "hxg": 0.8 + (i % 5) * 0.2,
                "axg": 0.6 + (i % 4) * 0.15,
                "season": 2024,
            }
        )
        day += 1
    return rows


def test_xg_benchmark_feature_shapes_match_rows():
    x_base, x_xg, y, meta, current = build_examples(_rows())

    assert len(y) > 0
    assert len(x_base) == len(x_xg) == len(y) == len(meta)
    assert x_base.shape[1] == len(BASE_FEATURES)
    assert x_xg.shape[1] == len(XG_FEATURES)
    assert len(XG_FEATURES) > len(BASE_FEATURES)
    assert {"Alpha", "Beta", "Gamma", "Delta"} <= set(current)


def test_features_are_pre_match_not_current_match():
    rows = _rows()
    x_base_a, x_xg_a, y_a, meta_a, _ = build_examples(rows)

    # Change only the final match. Its own result/xG must not alter its feature
    # vector because state is updated after the feature vector is created.
    changed = [dict(row) for row in rows]
    changed[-1]["hg"] = 9
    changed[-1]["ag"] = 0
    changed[-1]["hxg"] = 7.5
    changed[-1]["axg"] = 0.1

    x_base_b, x_xg_b, y_b, meta_b, _ = build_examples(changed)

    assert meta_a[-1] == meta_b[-1]
    assert (x_base_a[-1] == x_base_b[-1]).all()
    assert (x_xg_a[-1] == x_xg_b[-1]).all()
    # The label is allowed to change because that is what the model learns.
    assert len(y_a) == len(y_b)
