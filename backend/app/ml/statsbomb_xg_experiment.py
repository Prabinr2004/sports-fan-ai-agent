from __future__ import annotations

"""Research-only StatsBomb Open Data xG experiment.

Purpose: test whether rolling xG adds predictive signal on an open season with
broad match coverage. This never writes a production artifact.
"""

import json
from collections import defaultdict, deque

import httpx
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
COMPETITION_ID = 9
SEASON_ID = 281

# Match the download approach already used successfully by FanSphere's trainers.
# Some macOS/Python installations have an incomplete local CA chain for urllib.
_CLIENT = httpx.Client(timeout=60.0, follow_redirects=True)


def get_json(url: str):
    response = _CLIENT.get(url)
    response.raise_for_status()
    return response.json()


def avg(values, default=0.0):
    return float(sum(values) / len(values)) if values else float(default)


def brier(y, probs, classes):
    idx = {c: i for i, c in enumerate(classes)}
    onehot = np.zeros_like(probs)
    for row, label in enumerate(y):
        onehot[row, idx[label]] = 1.0
    return float(np.mean(np.sum((probs - onehot) ** 2, axis=1)))


def match_xg(match_id: int, home: str, away: str):
    events = get_json(f"{BASE}/events/{match_id}.json")
    totals = {home: 0.0, away: 0.0}
    shots = {home: 0, away: 0}
    for event in events:
        if event.get("type", {}).get("name") != "Shot":
            continue
        team = event.get("team", {}).get("name")
        if team not in totals:
            continue
        xg = event.get("shot", {}).get("statsbomb_xg")
        if xg is not None:
            totals[team] += float(xg)
            shots[team] += 1
    return totals[home], totals[away], shots[home], shots[away]


def build_dataset():
    matches = get_json(f"{BASE}/matches/{COMPETITION_ID}/{SEASON_ID}.json")
    matches.sort(key=lambda m: (m.get("match_date", ""), m.get("kick_off", "")))
    xg_for = defaultdict(lambda: deque(maxlen=5)); xg_against = defaultdict(lambda: deque(maxlen=5))
    goals_for = defaultdict(lambda: deque(maxlen=5)); goals_against = defaultdict(lambda: deque(maxlen=5))
    points = defaultdict(lambda: deque(maxlen=5))
    rows = []
    for i, m in enumerate(matches, 1):
        home = m["home_team"]["home_team_name"]
        away = m["away_team"]["away_team_name"]
        hg = int(m["home_score"]); ag = int(m["away_score"])
        hxg, axg, hshots, ashots = match_xg(int(m["match_id"]), home, away)
        if len(points[home]) >= 3 and len(points[away]) >= 3:
            common = [avg(points[home]), avg(points[away]), avg(goals_for[home]), avg(goals_for[away]), avg(goals_against[home]), avg(goals_against[away])]
            enriched = common + [avg(xg_for[home]), avg(xg_for[away]), avg(xg_against[home]), avg(xg_against[away])]
            label = "HOME" if hg > ag else "AWAY" if ag > hg else "DRAW"
            rows.append({"common": common, "xg": enriched, "label": label, "date": m.get("match_date"), "home": home, "away": away})
        hp, ap = (3., 0.) if hg > ag else ((1., 1.) if hg == ag else (0., 3.))
        points[home].append(hp); points[away].append(ap)
        goals_for[home].append(hg); goals_for[away].append(ag)
        goals_against[home].append(ag); goals_against[away].append(hg)
        xg_for[home].append(hxg); xg_for[away].append(axg)
        xg_against[home].append(axg); xg_against[away].append(hxg)
        if i % 50 == 0:
            print(f"Downloaded events for {i}/{len(matches)} matches...", flush=True)
    return rows


def evaluate(rows, field):
    x = np.asarray([r[field] for r in rows], float)
    y = np.asarray([r["label"] for r in rows])
    cut = int(len(y) * .75)
    model = Pipeline([("scale", StandardScaler()), ("model", LogisticRegression(max_iter=3000, C=.1))])
    model.fit(x[:cut], y[:cut])
    p = model.predict_proba(x[cut:]); pred = model.predict(x[cut:]); classes = list(model.classes_)
    return {"train_rows": cut, "test_rows": len(y)-cut, "accuracy": float(accuracy_score(y[cut:], pred)), "log_loss": float(log_loss(y[cut:], p, labels=classes)), "brier": brier(y[cut:], p, classes), "test_first": rows[cut]["date"], "test_last": rows[-1]["date"]}


def main():
    rows = build_dataset()
    result = {"source": "StatsBomb Open Data", "competition": "Bundesliga", "season": "2023/2024", "usable_rows": len(rows), "split": "chronological 75/25", "results_only_features": evaluate(rows, "common"), "results_plus_rolling_xg": evaluate(rows, "xg"), "decision_rule": "xG is useful only if held-out probability quality and/or accuracy improves enough to justify finding broader current xG coverage.", "production_changed": False}
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
