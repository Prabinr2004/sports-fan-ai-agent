from __future__ import annotations

"""Research-only Big Five xG benchmark using Understat's current JSON endpoints.

This script DOES NOT write production model artifacts. It compares the same
chronological match rows using (A) results/form features and (B) the same
features plus rolling pre-match xG. The in-progress 2026/27 season is fetched
only for current team state and is excluded from benchmark fitting/evaluation.
"""

import argparse
import json
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

import httpx
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

BASE = "https://understat.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE + "/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

LEAGUES = {
    "epl": {"name": "Premier League", "slug": "EPL"},
    "laliga": {"name": "La Liga", "slug": "La_liga"},
    "bundesliga": {"name": "Bundesliga", "slug": "Bundesliga"},
    "seriea": {"name": "Serie A", "slug": "Serie_A"},
    "ligue1": {"name": "Ligue 1", "slug": "Ligue_1"},
}

HISTORICAL_SEASONS = (2022, 2023, 2024, 2025)
CURRENT_SEASON = 2026
C_VALUES = (0.05, 0.1, 0.2, 0.35, 0.5, 0.8, 1.0)

BASE_FEATURES = [
    "home_ppg_5", "away_ppg_5",
    "home_ppg_10", "away_ppg_10",
    "home_venue_ppg_5", "away_venue_ppg_5",
    "home_gf_5", "away_gf_5",
    "home_ga_5", "away_ga_5",
    "home_gd_10", "away_gd_10",
    "home_elo", "away_elo", "elo_diff",
]

XG_FEATURES = BASE_FEATURES + [
    "home_xgf_5", "away_xgf_5",
    "home_xga_5", "away_xga_5",
    "home_xgd_10", "away_xgd_10",
]


@dataclass
class TeamState:
    elo: float = 1500.0


def avg(values, default: float = 1.35) -> float:
    return float(sum(values) / len(values)) if values else float(default)


def fetch_season(slug: str, season: int) -> list[dict[str, Any]]:
    page_url = f"{BASE}/league/{slug}/{season}"
    api_url = f"{BASE}/getLeagueData/{slug}/{season}"
    with httpx.Client(headers=HEADERS, timeout=45.0, follow_redirects=True) as client:
        page = client.get(page_url)
        page.raise_for_status()
        response = client.get(api_url)
        response.raise_for_status()
        payload = response.json()

    dates = payload.get("dates")
    if not isinstance(dates, list):
        raise RuntimeError(f"No dates list returned from {api_url}")

    rows: list[dict[str, Any]] = []
    for match in dates:
        if not match.get("isResult"):
            continue
        goals = match.get("goals") or {}
        xg = match.get("xG") or {}
        try:
            hg = int(goals.get("h"))
            ag = int(goals.get("a"))
            hxg = float(xg.get("h"))
            axg = float(xg.get("a"))
        except (TypeError, ValueError):
            continue
        rows.append({
            "date": match.get("datetime", ""),
            "home": (match.get("h") or {}).get("title", ""),
            "away": (match.get("a") or {}).get("title", ""),
            "hg": hg,
            "ag": ag,
            "hxg": hxg,
            "axg": axg,
            "season": season,
        })
    return rows


def download_league(key: str, include_current: bool = False) -> list[dict[str, Any]]:
    cfg = LEAGUES[key]
    seasons = list(HISTORICAL_SEASONS)
    if include_current:
        seasons.append(CURRENT_SEASON)
    rows: list[dict[str, Any]] = []
    for season in seasons:
        season_rows = fetch_season(cfg["slug"], season)
        rows.extend(season_rows)
        print(
            f"{cfg['name']} {season}/{str(season + 1)[-2:]}: "
            f"{len(season_rows)} completed matches with xG",
            flush=True,
        )
    rows.sort(key=lambda row: row["date"])
    return rows


def outcome(hg: int, ag: int) -> str:
    return "HOME" if hg > ag else "AWAY" if ag > hg else "DRAW"


def build_examples(rows: list[dict[str, Any]]):
    state = defaultdict(TeamState)
    points5 = defaultdict(lambda: deque(maxlen=5))
    points10 = defaultdict(lambda: deque(maxlen=10))
    homepoints5 = defaultdict(lambda: deque(maxlen=5))
    awaypoints5 = defaultdict(lambda: deque(maxlen=5))
    gf5 = defaultdict(lambda: deque(maxlen=5))
    ga5 = defaultdict(lambda: deque(maxlen=5))
    gd10 = defaultdict(lambda: deque(maxlen=10))
    xgf5 = defaultdict(lambda: deque(maxlen=5))
    xga5 = defaultdict(lambda: deque(maxlen=5))
    xgd10 = defaultdict(lambda: deque(maxlen=10))

    x_base: list[list[float]] = []
    x_xg: list[list[float]] = []
    y: list[str] = []
    meta: list[dict[str, Any]] = []

    for row in rows:
        h, a = row["home"], row["away"]
        hg, ag = int(row["hg"]), int(row["ag"])
        hxg, axg = float(row["hxg"]), float(row["axg"])

        # All features below are computed before this match is added to state.
        if (
            len(points5[h]) >= 3
            and len(points5[a]) >= 3
            and len(xgf5[h]) >= 3
            and len(xgf5[a]) >= 3
        ):
            he, ae = state[h].elo, state[a].elo
            base = [
                avg(points5[h]), avg(points5[a]),
                avg(points10[h]), avg(points10[a]),
                avg(homepoints5[h]), avg(awaypoints5[a]),
                avg(gf5[h]), avg(gf5[a]),
                avg(ga5[h]), avg(ga5[a]),
                avg(gd10[h], 0.0), avg(gd10[a], 0.0),
                he, ae, he - ae,
            ]
            richer = base + [
                avg(xgf5[h]), avg(xgf5[a]),
                avg(xga5[h]), avg(xga5[a]),
                avg(xgd10[h], 0.0), avg(xgd10[a], 0.0),
            ]
            x_base.append(base)
            x_xg.append(richer)
            y.append(outcome(hg, ag))
            meta.append({
                "date": row["date"],
                "season": row["season"],
                "home": h,
                "away": a,
            })

        result = outcome(hg, ag)
        hp, ap = (
            (3.0, 0.0) if result == "HOME"
            else (1.0, 1.0) if result == "DRAW"
            else (0.0, 3.0)
        )

        points5[h].append(hp)
        points5[a].append(ap)
        points10[h].append(hp)
        points10[a].append(ap)
        homepoints5[h].append(hp)
        awaypoints5[a].append(ap)
        gf5[h].append(float(hg))
        ga5[h].append(float(ag))
        gf5[a].append(float(ag))
        ga5[a].append(float(hg))
        gd10[h].append(float(hg - ag))
        gd10[a].append(float(ag - hg))
        xgf5[h].append(hxg)
        xga5[h].append(axg)
        xgf5[a].append(axg)
        xga5[a].append(hxg)
        xgd10[h].append(hxg - axg)
        xgd10[a].append(axg - hxg)

        expected = 1.0 / (1.0 + 10 ** ((state[a].elo - (state[h].elo + 60.0)) / 400.0))
        actual = 1.0 if result == "HOME" else 0.5 if result == "DRAW" else 0.0
        delta = 20.0 * (actual - expected)
        state[h].elo += delta
        state[a].elo -= delta

    current_state = {
        team: {
            "elo": round(team_state.elo, 2),
            "ppg_5": round(avg(points5[team]), 3),
            "xgf_5": round(avg(xgf5[team]), 3),
            "xga_5": round(avg(xga5[team]), 3),
            "xgd_10": round(avg(xgd10[team], 0.0), 3),
        }
        for team, team_state in state.items()
    }
    return (
        np.asarray(x_base, dtype=float),
        np.asarray(x_xg, dtype=float),
        np.asarray(y),
        meta,
        current_state,
    )


def multiclass_brier(y_true, probs, classes) -> float:
    truth = np.zeros_like(probs)
    lookup = {label: idx for idx, label in enumerate(classes)}
    for i, label in enumerate(y_true):
        truth[i, lookup[label]] = 1.0
    return float(np.mean(np.sum((probs - truth) ** 2, axis=1)))


def calibration_summary(y_true, probs, classes) -> list[dict[str, Any]]:
    # Calibration of the model's top-class confidence, useful as a compact
    # diagnostic without pretending match outcome probabilities are certainty.
    predicted_idx = np.argmax(probs, axis=1)
    predicted = np.asarray([classes[i] for i in predicted_idx])
    confidence = np.max(probs, axis=1)
    correct = predicted == y_true
    buckets = [(0.0, 0.4), (0.4, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 1.01)]
    result = []
    for lo, hi in buckets:
        mask = (confidence >= lo) & (confidence < hi)
        if not np.any(mask):
            continue
        result.append({
            "confidence_range": f"{lo:.1f}-{min(hi, 1.0):.1f}",
            "rows": int(mask.sum()),
            "mean_confidence": float(confidence[mask].mean()),
            "accuracy": float(correct[mask].mean()),
        })
    return result


def make_model(c: float):
    return Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(max_iter=2500, C=c)),
    ])


def evaluate_variant(x, y, train_end: int, val_end: int):
    best_c = None
    best_loss = float("inf")
    trials = []

    for c in C_VALUES:
        model = make_model(c)
        model.fit(x[:train_end], y[:train_end])
        probs = model.predict_proba(x[train_end:val_end])
        classes = model.classes_
        loss = float(log_loss(y[train_end:val_end], probs, labels=classes))
        trials.append({"C": c, "validation_log_loss": loss})
        if loss < best_loss:
            best_loss = loss
            best_c = c

    model = make_model(float(best_c))
    model.fit(x[:val_end], y[:val_end])
    probs = model.predict_proba(x[val_end:])
    pred = model.predict(x[val_end:])
    classes = model.classes_

    return {
        "selected_C": best_c,
        "validation_log_loss": best_loss,
        "test_accuracy": float(accuracy_score(y[val_end:], pred)),
        "test_log_loss": float(log_loss(y[val_end:], probs, labels=classes)),
        "test_brier": multiclass_brier(y[val_end:], probs, classes),
        "calibration": calibration_summary(y[val_end:], probs, classes),
        "candidate_trials": trials,
    }


def benchmark_league(key: str) -> dict[str, Any]:
    # Fetch each season only once. 2026/27 is included for state only.
    through_current = download_league(key, include_current=True)
    historical = [row for row in through_current if row["season"] != CURRENT_SEASON]
    current_raw = [row for row in through_current if row["season"] == CURRENT_SEASON]

    x_base, x_xg, y, meta, _ = build_examples(historical)
    n = len(y)
    train_end = int(n * 0.70)
    val_end = int(n * 0.80)
    if train_end < 100 or val_end <= train_end or val_end >= n:
        raise RuntimeError(f"Not enough benchmark rows for {LEAGUES[key]['name']}: {n}")

    baseline = evaluate_variant(x_base, y, train_end, val_end)
    richer = evaluate_variant(x_xg, y, train_end, val_end)

    # Build current state from history + completed 2026/27 matches after metrics
    # are finalized. This state never influences the benchmark split.
    _, _, _, current_meta, current_state = build_examples(through_current)
    current_feature_rows = [m for m in current_meta if m["season"] == CURRENT_SEASON]
    current_teams = {
        team
        for row in current_raw
        for team in (row["home"], row["away"])
        if team
    }

    return {
        "league": LEAGUES[key]["name"],
        "historical_seasons": ["2022/23", "2023/24", "2024/25", "2025/26"],
        "current_state_season": "2026/27",
        "benchmark_rows": n,
        "train_rows": train_end,
        "validation_rows": val_end - train_end,
        "test_rows": n - val_end,
        "test_first_match": meta[val_end],
        "test_last_match": meta[-1],
        "results_only": baseline,
        "results_plus_rolling_xg": richer,
        "delta_log_loss_xg_minus_baseline": richer["test_log_loss"] - baseline["test_log_loss"],
        "delta_brier_xg_minus_baseline": richer["test_brier"] - baseline["test_brier"],
        "delta_accuracy_xg_minus_baseline": richer["test_accuracy"] - baseline["test_accuracy"],
        "current_2026_27_completed_feature_rows": len(current_rows),
        "current_team_states": len(current_state),
        "production_changed": False,
    }


def main():
    parser = argparse.ArgumentParser(description="Research-only Understat xG benchmark")
    parser.add_argument(
        "--league",
        choices=[*LEAGUES.keys(), "all"],
        default="all",
        help="Run one league first for a network smoke test, or all five.",
    )
    args = parser.parse_args()
    selected = list(LEAGUES) if args.league == "all" else [args.league]

    results: dict[str, Any] = {
        "source": "Understat current JSON endpoints",
        "method": "chronological 70/10/20, same rows for baseline and xG variant",
        "requested_league": args.league,
        "production_changed": False,
        "leagues": {},
    }
    for key in selected:
        try:
            results["leagues"][key] = benchmark_league(key)
        except Exception as exc:
            results["leagues"][key] = {
                "league": LEAGUES[key]["name"],
                "error": str(exc),
                "production_changed": False,
            }

    wins = []
    for key, result in results["leagues"].items():
        if "error" in result:
            continue
        if (
            result["delta_log_loss_xg_minus_baseline"] < 0
            and result["delta_brier_xg_minus_baseline"] < 0
        ):
            wins.append(key)
    results["xg_probability_quality_wins"] = wins
    results["promotion_rule"] = (
        "Do not promote from this research benchmark alone. xG must improve "
        "held-out probability quality across multiple leagues, then be integrated "
        "into the production trainer and revalidated."
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
