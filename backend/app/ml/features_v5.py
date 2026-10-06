from __future__ import annotations

"""Richer pre-match features for the v5 domestic experiment.

All values are computed from matches that happened before the target fixture.
No future-match information is used.
"""

from collections import defaultdict, deque
from datetime import date
import numpy as np

from app.ml.training import TeamState, _avg, normalize_team_name

FEATURE_NAMES_V5 = [
    "home_ppg_5", "away_ppg_5", "home_ppg_10", "away_ppg_10",
    "home_venue_ppg_5", "away_venue_ppg_5",
    "home_gf_5", "away_gf_5", "home_ga_5", "away_ga_5",
    "home_gd_10", "away_gd_10",
    "home_elo", "away_elo", "elo_diff",
    "home_rest_days", "away_rest_days", "rest_diff",
    "home_strength_form_5", "away_strength_form_5", "strength_form_diff",
    "home_scoring_rate_10", "away_scoring_rate_10",
    "home_concede_rate_10", "away_concede_rate_10",
]


def _parse_day(value: str) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _rest(current: date | None, previous: date | None) -> float:
    if current is None or previous is None:
        return 7.0
    # Cap long international/summer breaks so they do not dominate scaling.
    return float(max(2, min(21, (current - previous).days)))


def build_examples_v5(rows):
    state = defaultdict(TeamState)
    points5 = defaultdict(lambda: deque(maxlen=5))
    points10 = defaultdict(lambda: deque(maxlen=10))
    home_points5 = defaultdict(lambda: deque(maxlen=5))
    away_points5 = defaultdict(lambda: deque(maxlen=5))
    gf5 = defaultdict(lambda: deque(maxlen=5))
    ga5 = defaultdict(lambda: deque(maxlen=5))
    gf10 = defaultdict(lambda: deque(maxlen=10))
    ga10 = defaultdict(lambda: deque(maxlen=10))
    gd10 = defaultdict(lambda: deque(maxlen=10))
    strength_form5 = defaultdict(lambda: deque(maxlen=5))
    last_date = {}
    match_count = defaultdict(int)

    x, y, meta = [], [], []
    for r in rows:
        h, a, hg, ag = r["home"], r["away"], r["hg"], r["ag"]
        day = _parse_day(r.get("date"))
        if len(points5[h]) >= 3 and len(points5[a]) >= 3:
            he, ae = state[h].elo, state[a].elo
            hr, ar = _rest(day, last_date.get(h)), _rest(day, last_date.get(a))
            hs, ass = _avg(strength_form5[h], 0.0), _avg(strength_form5[a], 0.0)
            x.append([
                _avg(points5[h]), _avg(points5[a]), _avg(points10[h]), _avg(points10[a]),
                _avg(home_points5[h]), _avg(away_points5[a]),
                _avg(gf5[h]), _avg(gf5[a]), _avg(ga5[h]), _avg(ga5[a]),
                _avg(gd10[h], 0.0), _avg(gd10[a], 0.0),
                he, ae, he - ae,
                hr, ar, hr - ar,
                hs, ass, hs - ass,
                _avg(gf10[h]), _avg(gf10[a]), _avg(ga10[h]), _avg(ga10[a]),
            ])
            y.append("HOME" if hg > ag else "AWAY" if ag > hg else "DRAW")
            meta.append({"date": r.get("date"), "season": r.get("season"), "home": h, "away": a})

        result = "HOME" if hg > ag else "AWAY" if ag > hg else "DRAW"
        hp, ap = (3.0, 0.0) if result == "HOME" else ((1.0, 1.0) if result == "DRAW" else (0.0, 3.0))
        pre_he, pre_ae = state[h].elo, state[a].elo
        # Result quality relative to opponent strength. Beating a stronger side is
        # worth more than beating a weaker side; values remain pre-match derived.
        strength_form5[h].append((hp - 1.0) + (pre_ae - 1500.0) / 400.0)
        strength_form5[a].append((ap - 1.0) + (pre_he - 1500.0) / 400.0)

        points5[h].append(hp); points5[a].append(ap)
        points10[h].append(hp); points10[a].append(ap)
        home_points5[h].append(hp); away_points5[a].append(ap)
        gf5[h].append(float(hg)); gf5[a].append(float(ag))
        ga5[h].append(float(ag)); ga5[a].append(float(hg))
        gf10[h].append(float(hg)); gf10[a].append(float(ag))
        ga10[h].append(float(ag)); ga10[a].append(float(hg))
        gd10[h].append(float(hg - ag)); gd10[a].append(float(ag - hg))

        expected = 1 / (1 + 10 ** ((state[a].elo - (state[h].elo + 60)) / 400))
        actual = 1.0 if result == "HOME" else 0.5 if result == "DRAW" else 0.0
        delta = 20 * (actual - expected)
        state[h].elo += delta; state[a].elo -= delta
        last_date[h] = day; last_date[a] = day
        match_count[h] += 1; match_count[a] += 1

    current = {}
    for t, s in state.items():
        current[normalize_team_name(t)] = {
            "name": t, "elo": s.elo,
            "ppg_5": _avg(points5[t]), "ppg_10": _avg(points10[t]),
            "home_ppg_5": _avg(home_points5[t]), "away_ppg_5": _avg(away_points5[t]),
            "gf_5": _avg(gf5[t]), "ga_5": _avg(ga5[t]),
            "gf_10": _avg(gf10[t]), "ga_10": _avg(ga10[t]),
            "gd_10": _avg(gd10[t], 0.0),
            "strength_form_5": _avg(strength_form5[t], 0.0),
            "last_match_date": last_date.get(t).isoformat() if last_date.get(t) else None,
            "matches": match_count[t],
        }
    return np.asarray(x, float), np.asarray(y), meta, current
