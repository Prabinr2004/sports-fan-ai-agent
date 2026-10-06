from app.ml.understat_xg_benchmark import (
    ADVANCED_FEATURES,
    BASE_FEATURES,
    XG_FEATURES,
    build_examples,
)


def _rows():
    rows = []
    teams = ["Alpha", "Beta", "Gamma", "Delta"]
    pairings = [
        ("Alpha", "Beta"), ("Gamma", "Delta"), ("Beta", "Gamma"), ("Delta", "Alpha"),
        ("Alpha", "Gamma"), ("Beta", "Delta"), ("Gamma", "Alpha"), ("Delta", "Beta"),
        ("Alpha", "Beta"), ("Gamma", "Delta"), ("Beta", "Gamma"), ("Delta", "Alpha"),
        ("Alpha", "Gamma"), ("Beta", "Delta"), ("Gamma", "Alpha"), ("Delta", "Beta"),
    ]
    for i, (home, away) in enumerate(pairings):
        hg, ag = (i + 1) % 3, i % 2
        hxg, axg = 0.8 + (i % 5) * 0.2, 0.6 + (i % 4) * 0.15
        rows.append({
            "date": f"2025-01-{i + 1:02d} 15:00:00", "home": home, "away": away,
            "hg": hg, "ag": ag, "hxg": hxg, "axg": axg, "season": 2024,
            "hnpxg": max(0.0, hxg - 0.1), "anpxg": max(0.0, axg - 0.1),
            "hnpxga": max(0.0, axg - 0.1), "anpxga": max(0.0, hxg - 0.1),
            "hxpts": 1.4 + (i % 3) * 0.1, "axpts": 1.2 + (i % 2) * 0.1,
            "hppda": 9.0 + (i % 4), "appda": 10.0 + (i % 3),
            "hdeep": 5.0 + (i % 4), "adeep": 4.0 + (i % 3),
        })
    return rows


def test_feature_shapes_match_rows():
    x_base, x_xg, x_advanced, y, meta, current = build_examples(_rows())
    assert len(y) > 0
    assert len(x_base) == len(x_xg) == len(x_advanced) == len(y) == len(meta)
    assert x_base.shape[1] == len(BASE_FEATURES)
    assert x_xg.shape[1] == len(XG_FEATURES)
    assert x_advanced.shape[1] == len(ADVANCED_FEATURES)
    assert len(ADVANCED_FEATURES) > len(XG_FEATURES) > len(BASE_FEATURES)
    assert {"Alpha", "Beta", "Gamma", "Delta"} <= set(current)


def test_features_are_pre_match_not_current_match():
    rows = _rows()
    b1, x1, a1, y1, m1, _ = build_examples(rows)
    changed = [dict(row) for row in rows]
    changed[-1].update({"hg": 9, "ag": 0, "hxg": 7.5, "axg": 0.1, "hnpxg": 7.0,
                        "anpxg": 0.1, "hxpts": 2.9, "axpts": 0.1, "hppda": 3.0,
                        "appda": 20.0, "hdeep": 20.0, "adeep": 1.0})
    b2, x2, a2, y2, m2, _ = build_examples(changed)
    assert m1[-1] == m2[-1]
    assert (b1[-1] == b2[-1]).all()
    assert (x1[-1] == x2[-1]).all()
    assert (a1[-1] == a2[-1]).all()
    assert len(y1) == len(y2)
