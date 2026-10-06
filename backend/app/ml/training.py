from __future__ import annotations

import csv
import io
import json
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss

FEATURE_NAMES = [
    "home_ppg_5", "away_ppg_5", "home_gf_5", "away_gf_5",
    "home_ga_5", "away_ga_5", "home_elo", "away_elo", "elo_diff",
]
CLASSES = ["HOME", "DRAW", "AWAY"]
SEASONS = ("2223", "2324", "2425", "2526", "2627")
DATA_URL = "https://www.football-data.co.uk/mmz4281/{season}/E0.csv"


@dataclass
class TeamState:
    elo: float = 1500.0


def _outcome(row: dict[str, str]) -> str:
    value = (row.get("FTR") or "").strip()
    return {"H": "HOME", "D": "DRAW", "A": "AWAY"}[value]


def _avg(values: deque[float], default: float) -> float:
    return sum(values) / len(values) if values else default


def _date(row: dict[str, str]) -> datetime:
    raw = (row.get("Date") or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    return datetime.min


def download_epl_rows() -> list[dict[str, str]]:
    """Download EPL CSVs using httpx/certifi instead of macOS urllib's certificate store."""
    rows: list[dict[str, str]] = []
    headers = {"User-Agent": "FanSphere-ML/1.0"}
    with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
        for season in SEASONS:
            url = DATA_URL.format(season=season)
            try:
                response = client.get(url)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise RuntimeError(f"Could not download EPL season {season} from {url}: {exc}") from exc
            text = response.content.decode("utf-8-sig", errors="replace")
            season_rows = 0
            for row in csv.DictReader(io.StringIO(text)):
                if row.get("HomeTeam") and row.get("AwayTeam") and row.get("FTR") in {"H", "D", "A"}:
                    row["_season"] = season
                    rows.append(row)
                    season_rows += 1
            print(f"Loaded season {season}: {season_rows} completed matches")
    rows.sort(key=_date)
    return rows


def build_examples(rows: list[dict[str, str]]) -> tuple[np.ndarray, np.ndarray, list[dict[str, str]]]:
    state: dict[str, TeamState] = defaultdict(TeamState)
    points: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=5))
    gf: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=5))
    ga: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=5))
    x: list[list[float]] = []
    y: list[str] = []
    meta: list[dict[str, str]] = []

    for row in rows:
        home, away = row["HomeTeam"], row["AwayTeam"]
        if len(points[home]) >= 3 and len(points[away]) >= 3:
            home_ppg = _avg(points[home], 1.35)
            away_ppg = _avg(points[away], 1.35)
            home_gf = _avg(gf[home], 1.35)
            away_gf = _avg(gf[away], 1.35)
            home_ga = _avg(ga[home], 1.35)
            away_ga = _avg(ga[away], 1.35)
            home_elo, away_elo = state[home].elo, state[away].elo
            x.append([home_ppg, away_ppg, home_gf, away_gf, home_ga, away_ga, home_elo, away_elo, home_elo-away_elo])
            y.append(_outcome(row))
            meta.append({"date": row.get("Date", ""), "season": row.get("_season", ""), "home": home, "away": away})

        hg, ag = int(float(row.get("FTHG") or 0)), int(float(row.get("FTAG") or 0))
        result = _outcome(row)
        hp, ap = (3.0, 0.0) if result == "HOME" else ((1.0, 1.0) if result == "DRAW" else (0.0, 3.0))
        points[home].append(hp); points[away].append(ap)
        gf[home].append(float(hg)); ga[home].append(float(ag))
        gf[away].append(float(ag)); ga[away].append(float(hg))

        expected_home = 1.0 / (1.0 + 10 ** ((state[away].elo - (state[home].elo + 60.0)) / 400.0))
        actual_home = 1.0 if result == "HOME" else (0.5 if result == "DRAW" else 0.0)
        delta = 20.0 * (actual_home - expected_home)
        state[home].elo += delta; state[away].elo -= delta

    return np.asarray(x, dtype=float), np.asarray(y), meta


def multiclass_brier(y_true: np.ndarray, probabilities: np.ndarray, classes: np.ndarray) -> float:
    truth = np.zeros_like(probabilities)
    lookup = {label: i for i, label in enumerate(classes)}
    for row, label in enumerate(y_true):
        truth[row, lookup[label]] = 1.0
    return float(np.mean(np.sum((probabilities - truth) ** 2, axis=1)))


def train(output_dir: Path) -> dict:
    rows = download_epl_rows()
    x, y, meta = build_examples(rows)
    if len(y) < 100:
        raise RuntimeError("Not enough historical matches to train the model.")

    split = int(len(y) * 0.8)
    x_train, x_test = x[:split], x[split:]
    y_train, y_test = y[:split], y[split:]
    model = LogisticRegression(max_iter=2500, C=0.35, class_weight="balanced")
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)
    predictions = model.predict(x_test)

    metrics = {
        "model_version": "epl-logreg-v1",
        "model_type": "multinomial-logistic-regression",
        "features": FEATURE_NAMES,
        "rows_total": int(len(y)),
        "train_rows": int(len(y_train)),
        "test_rows": int(len(y_test)),
        "chronological_split": True,
        "test_accuracy": float(accuracy_score(y_test, predictions)),
        "test_log_loss": float(log_loss(y_test, probabilities, labels=model.classes_)),
        "test_brier": multiclass_brier(y_test, probabilities, model.classes_),
        "test_first_match": meta[split] if split < len(meta) else None,
        "test_last_match": meta[-1] if meta else None,
        "data_source": "football-data.co.uk historical EPL results",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_names": FEATURE_NAMES}, output_dir / "epl_logreg_v1.joblib")
    (output_dir / "epl_logreg_v1_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "artifacts"
    print(json.dumps(train(target), indent=2))
