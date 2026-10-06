from __future__ import annotations

"""Research-only Big Five xG benchmark using Understat's current JSON endpoints.

Compares results/form features against richer rolling pre-match Understat team
metrics. The in-progress 2026/27 season is state-only and never enters the
historical benchmark fit/test rows. No production artifact is written.
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
C_VALUES = (0.02, 0.05, 0.1, 0.2, 0.35, 0.5)

BASE_FEATURES = [
    "home_ppg_5", "away_ppg_5", "home_ppg_10", "away_ppg_10",
    "home_venue_ppg_5", "away_venue_ppg_5", "home_gf_5", "away_gf_5",
    "home_ga_5", "away_ga_5", "home_gd_10", "away_gd_10",
    "home_elo", "away_elo", "elo_diff",
]

XG_FEATURES = BASE_FEATURES + [
    "home_xgf_5", "away_xgf_5", "home_xga_5", "away_xga_5",
    "home_xgd_10", "away_xgd_10",
]

ADVANCED_FEATURES = XG_FEATURES + [
    "home_npxgf_5", "away_npxgf_5", "home_npxga_5", "away_npxga_5",
    "home_xpts_5", "away_xpts_5", "home_ppda_5", "away_ppda_5",
    "home_deep_5", "away_deep_5",
]


@dataclass
class TeamState:
    elo: float = 1500.0


def avg(values, default: float = 1.35) -> float:
    return float(sum(values) / len(values)) if values else float(default)


def _f(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _team_history_by_date(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    teams = payload.get("teams") or {}
    for team in teams.values():
        title = team.get("title", "")
        for match in team.get("history") or []:
            date = match.get("date", "")
            if title and date:
                result[(title, date)] = match
    return result


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
    history = _team_history_by_date(payload)

    rows: list[dict[str, Any]] = []
    for match in dates:
        if not match.get("isResult"):
            continue
        goals, xg = match.get("goals") or {}, match.get("xG") or {}
        home = (match.get("h") or {}).get("title", "")
        away = (match.get("a") or {}).get("title", "")
        date = match.get("datetime", "")
        date_key = date.split(" ")[0]
        hh = history.get((home, date_key), {})
        ah = history.get((away, date_key), {})
        try:
            hg, ag = int(goals.get("h")), int(goals.get("a"))
            hxg, axg = float(xg.get("h")), float(xg.get("a"))
        except (TypeError, ValueError):
            continue

        def ppda(hist):
            p = hist.get("ppda") or {}
            den = _f(p.get("def"), 0.0)
            return _f(p.get("att"), 0.0) / den if den else 0.0

        rows.append({
            "date": date, "home": home, "away": away, "hg": hg, "ag": ag,
            "hxg": hxg, "axg": axg, "season": season,
            "hnpxg": _f(hh.get("npxG"), hxg), "anpxg": _f(ah.get("npxG"), axg),
            "hnpxga": _f(hh.get("npxGA"), axg), "anpxga": _f(ah.get("npxGA"), hxg),
            "hxpts": _f(hh.get("xpts"), 1.35), "axpts": _f(ah.get("xpts"), 1.35),
            "hppda": ppda(hh), "appda": ppda(ah),
            "hdeep": _f(hh.get("deep"), 0.0), "adeep": _f(ah.get("deep"), 0.0),
        })
    return rows


def download_league(key: str, include_current: bool = False) -> list[dict[str, Any]]:
    cfg = LEAGUES[key]
    seasons = list(HISTORICAL_SEASONS) + ([CURRENT_SEASON] if include_current else [])
    rows: list[dict[str, Any]] = []
    for season in seasons:
        season_rows = fetch_season(cfg["slug"], season)
        rows.extend(season_rows)
        print(f"{cfg['name']} {season}/{str(season + 1)[-2:]}: {len(season_rows)} completed matches", flush=True)
    rows.sort(key=lambda row: row["date"])
    return rows


def outcome(hg: int, ag: int) -> str:
    return "HOME" if hg > ag else "AWAY" if ag > hg else "DRAW"


def build_examples(rows: list[dict[str, Any]]):
    state = defaultdict(TeamState)
    d5 = lambda: defaultdict(lambda: deque(maxlen=5))
    d10 = lambda: defaultdict(lambda: deque(maxlen=10))
    points5, points10, homepoints5, awaypoints5 = d5(), d10(), d5(), d5()
    gf5, ga5, gd10 = d5(), d5(), d10()
    xgf5, xga5, xgd10 = d5(), d5(), d10()
    npxgf5, npxga5, xpts5, ppda5, deep5 = d5(), d5(), d5(), d5(), d5()

    xb, xx, xa, y, meta = [], [], [], [], []
    for row in rows:
        h, a = row["home"], row["away"]
        hg, ag, hxg, axg = int(row["hg"]), int(row["ag"]), float(row["hxg"]), float(row["axg"])
        if len(points5[h]) >= 3 and len(points5[a]) >= 3:
            he, ae = state[h].elo, state[a].elo
            base = [avg(points5[h]), avg(points5[a]), avg(points10[h]), avg(points10[a]),
                    avg(homepoints5[h]), avg(awaypoints5[a]), avg(gf5[h]), avg(gf5[a]),
                    avg(ga5[h]), avg(ga5[a]), avg(gd10[h], 0), avg(gd10[a], 0), he, ae, he-ae]
            xg = base + [avg(xgf5[h]), avg(xgf5[a]), avg(xga5[h]), avg(xga5[a]),
                         avg(xgd10[h], 0), avg(xgd10[a], 0)]
            advanced = xg + [avg(npxgf5[h]), avg(npxgf5[a]), avg(npxga5[h]), avg(npxga5[a]),
                             avg(xpts5[h]), avg(xpts5[a]), avg(ppda5[h], 10), avg(ppda5[a], 10),
                             avg(deep5[h], 0), avg(deep5[a], 0)]
            xb.append(base); xx.append(xg); xa.append(advanced); y.append(outcome(hg, ag))
            meta.append({"date": row["date"], "season": row["season"], "home": h, "away": a})

        result = outcome(hg, ag)
        hp, ap = ((3., 0.) if result == "HOME" else (1., 1.) if result == "DRAW" else (0., 3.))
        for d, team, val in [(points5,h,hp),(points5,a,ap),(points10,h,hp),(points10,a,ap)]: d[team].append(val)
        homepoints5[h].append(hp); awaypoints5[a].append(ap)
        gf5[h].append(hg); ga5[h].append(ag); gf5[a].append(ag); ga5[a].append(hg)
        gd10[h].append(hg-ag); gd10[a].append(ag-hg)
        xgf5[h].append(hxg); xga5[h].append(axg); xgf5[a].append(axg); xga5[a].append(hxg)
        xgd10[h].append(hxg-axg); xgd10[a].append(axg-hxg)
        npxgf5[h].append(row["hnpxg"]); npxgf5[a].append(row["anpxg"])
        npxga5[h].append(row["hnpxga"]); npxga5[a].append(row["anpxga"])
        xpts5[h].append(row["hxpts"]); xpts5[a].append(row["axpts"])
        ppda5[h].append(row["hppda"]); ppda5[a].append(row["appda"])
        deep5[h].append(row["hdeep"]); deep5[a].append(row["adeep"])
        expected = 1/(1+10**((state[a].elo-(state[h].elo+60))/400))
        actual = 1. if result == "HOME" else .5 if result == "DRAW" else 0.
        delta = 20*(actual-expected); state[h].elo += delta; state[a].elo -= delta

    current = {t:{"elo":round(s.elo,2),"ppg_5":round(avg(points5[t]),3),"xgf_5":round(avg(xgf5[t]),3),
                  "xga_5":round(avg(xga5[t]),3),"xgd_10":round(avg(xgd10[t],0),3)} for t,s in state.items()}
    return np.asarray(xb,float), np.asarray(xx,float), np.asarray(xa,float), np.asarray(y), meta, current


def multiclass_brier(y_true, probs, classes) -> float:
    truth = np.zeros_like(probs); lookup = {label:i for i,label in enumerate(classes)}
    for i,label in enumerate(y_true): truth[i,lookup[label]] = 1.
    return float(np.mean(np.sum((probs-truth)**2, axis=1)))


def calibration_summary(y_true, probs, classes):
    idx=np.argmax(probs,axis=1); pred=np.asarray([classes[i] for i in idx]); conf=np.max(probs,axis=1); correct=pred==y_true
    result=[]
    for lo,hi in [(0,.4),(.4,.5),(.5,.6),(.6,.7),(.7,1.01)]:
        mask=(conf>=lo)&(conf<hi)
        if np.any(mask): result.append({"confidence_range":f"{lo:.1f}-{min(hi,1):.1f}","rows":int(mask.sum()),"mean_confidence":float(conf[mask].mean()),"accuracy":float(correct[mask].mean())})
    return result


def make_model(c):
    return Pipeline([("scaler",StandardScaler()),("classifier",LogisticRegression(max_iter=2500,C=c))])


def evaluate_variant(x,y,train_end,val_end):
    best_c,best_loss=None,float("inf")
    for c in C_VALUES:
        m=make_model(c); m.fit(x[:train_end],y[:train_end]); p=m.predict_proba(x[train_end:val_end]); loss=float(log_loss(y[train_end:val_end],p,labels=m.classes_))
        if loss<best_loss: best_c,best_loss=c,loss
    m=make_model(best_c); m.fit(x[:val_end],y[:val_end]); p=m.predict_proba(x[val_end:]); pred=m.predict(x[val_end:])
    return {"selected_C":best_c,"validation_log_loss":best_loss,"test_accuracy":float(accuracy_score(y[val_end:],pred)),
            "test_log_loss":float(log_loss(y[val_end:],p,labels=m.classes_)),"test_brier":multiclass_brier(y[val_end:],p,m.classes_),
            "calibration":calibration_summary(y[val_end:],p,m.classes_)}


def benchmark_league(key):
    all_rows=download_league(key,True); hist=[r for r in all_rows if r["season"]!=CURRENT_SEASON]; current_raw=[r for r in all_rows if r["season"]==CURRENT_SEASON]
    xb,xx,xa,y,meta,_=build_examples(hist); n=len(y); tr=int(n*.70); va=int(n*.80)
    if tr<100 or va<=tr or va>=n: raise RuntimeError(f"Not enough rows for {LEAGUES[key]['name']}: {n}")
    base=evaluate_variant(xb,y,tr,va); xg=evaluate_variant(xx,y,tr,va); advanced=evaluate_variant(xa,y,tr,va)
    _,_,_,_,current_meta,current_state=build_examples(all_rows)
    current_feature=[m for m in current_meta if m["season"]==CURRENT_SEASON]
    active={t for r in current_raw for t in (r["home"],r["away"]) if t}
    return {"league":LEAGUES[key]["name"],"benchmark_rows":n,"test_rows":n-va,"test_first_match":meta[va],"test_last_match":meta[-1],
            "results_only":base,"results_plus_rolling_xg":xg,"results_plus_understat_team_stats":advanced,
            "advanced_delta_log_loss":advanced["test_log_loss"]-base["test_log_loss"],"advanced_delta_brier":advanced["test_brier"]-base["test_brier"],
            "advanced_delta_accuracy":advanced["test_accuracy"]-base["test_accuracy"],"current_2026_27_completed_matches":len(current_raw),
            "current_2026_27_feature_rows":len(current_feature),"current_2026_27_active_teams":len(active),
            "current_state_total_teams_including_prior_seasons":len(current_state),"current_state_has_all_active_teams":all(t in current_state for t in active),
            "production_changed":False}


def main():
    parser=argparse.ArgumentParser(description="Research-only Understat richer-stat benchmark")
    parser.add_argument("--league",choices=[*LEAGUES.keys(),"all"],default="all"); args=parser.parse_args()
    selected=list(LEAGUES) if args.league=="all" else [args.league]
    results={"source":"Understat current JSON endpoints","method":"chronological 70/10/20; current 2026/27 state-only","requested_league":args.league,"production_changed":False,"leagues":{}}
    for key in selected:
        try: results["leagues"][key]=benchmark_league(key)
        except Exception as exc: results["leagues"][key]={"league":LEAGUES[key]["name"],"error":str(exc),"production_changed":False}
    wins=[]
    for key,r in results["leagues"].items():
        if "error" not in r and r["advanced_delta_log_loss"]<0 and r["advanced_delta_brier"]<0: wins.append(key)
    results["advanced_probability_quality_wins"]=wins
    results["promotion_rule"]="Research only. Do not change production unless richer Understat features improve held-out probability quality across multiple leagues and pass production-trainer revalidation."
    print(json.dumps(results,indent=2))


if __name__=="__main__": main()
