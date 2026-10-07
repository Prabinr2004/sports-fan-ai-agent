from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.profile import _get_or_create_local_user
from app.database.session import get_db
from app.models.prediction import UserMatchPrediction
from app.models.progress import XPEvent
from app.models.team import Team
from app.models.user import UserFavoriteTeam
from app.services.football import get_football_provider
from app.services.progress import progress_summary
from app.services.prediction_results import actual_outcome, parse_utc, result_check_due

router = APIRouter(prefix="/matches", tags=["matches"])


class PredictionChoice(BaseModel):
    outcome: str


def _saved_team_ids(db: Session, user) -> list[str]:
    team_ids: list[str] = []
    if user.primary_team:
        team_ids.append(user.primary_team.provider_id)
    links = db.scalars(select(UserFavoriteTeam).where(UserFavoriteTeam.user_id == user.id)).all()
    for link in links:
        team = db.get(Team, link.team_id)
        if team and team.provider_id not in team_ids:
            team_ids.append(team.provider_id)
    return team_ids[:6]


def _fixture_payload(fixture: dict, provider_team_id: str, saved: UserMatchPrediction | None = None) -> dict:
    kickoff = parse_utc(fixture.get("utc_date"))
    return {**fixture, "source_team_id": provider_team_id, "user_prediction": saved.predicted_outcome if saved else None, "prediction_locked": bool(kickoff and kickoff <= datetime.now(timezone.utc))}


async def _find_personalized_match(db: Session, user, match_id: str) -> dict | None:
    provider = get_football_provider()
    for provider_team_id in _saved_team_ids(db, user):
        try:
            fixtures = await provider.get_fixtures(provider_team_id)
        except (httpx.HTTPError, HTTPException):
            continue
        for fixture in fixtures:
            if str(fixture.get("id")) == str(match_id):
                return fixture
    return None


@router.get("")
async def personalized_matches(db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    team_ids = _saved_team_ids(db, user)
    if not team_ids:
        return {"matches": [], "notice": "Choose a primary team or follow teams to build your match feed."}
    provider = get_football_provider()
    collected: dict[str, dict] = {}
    unavailable = 0
    for provider_team_id in team_ids:
        try:
            fixtures = await provider.get_fixtures(provider_team_id)
        except (httpx.HTTPError, HTTPException):
            unavailable += 1
            continue
        for fixture in fixtures:
            match_id = str(fixture.get("id"))
            if match_id and match_id not in collected:
                saved = db.scalar(select(UserMatchPrediction).where(UserMatchPrediction.user_id == user.id, UserMatchPrediction.match_id == match_id))
                collected[match_id] = _fixture_payload(fixture, provider_team_id, saved)
    matches = sorted(collected.values(), key=lambda match: match.get("utc_date") or "")
    notice = "Some followed-team fixtures are unavailable on the current football data plan." if unavailable else None
    return {"matches": matches[:30], "notice": notice}


@router.get("/{match_id}/center")
async def match_center(match_id: str, db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    fixture = await _find_personalized_match(db, user, match_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="This match is not available in your personalized match feed.")

    provider = get_football_provider()
    saved = db.scalar(select(UserMatchPrediction).where(
        UserMatchPrediction.user_id == user.id,
        UserMatchPrediction.match_id == match_id,
    ))

    async def team_form(team: dict) -> dict:
        team_id = str(team.get("id"))
        try:
            results = await provider.get_recent_results(team_id, limit=5)
        except (httpx.HTTPError, HTTPException):
            return {"team_id": team_id, "form": [], "points": 0, "goals_for": 0, "goals_against": 0, "matches": 0}

        form: list[str] = []
        points = goals_for = goals_against = 0
        for result in results:
            home = result.get("home_team") or {}
            away = result.get("away_team") or {}
            score = result.get("score") or {}
            home_score, away_score = score.get("home"), score.get("away")
            if home_score is None or away_score is None:
                continue
            is_home = str(home.get("id")) == team_id
            gf, ga = (home_score, away_score) if is_home else (away_score, home_score)
            goals_for += gf
            goals_against += ga
            if gf > ga:
                form.append("W")
                points += 3
            elif gf == ga:
                form.append("D")
                points += 1
            else:
                form.append("L")
        return {"team_id": team_id, "form": form, "points": points, "goals_for": goals_for, "goals_against": goals_against, "matches": len(form)}

    home = fixture.get("home_team") or {}
    away = fixture.get("away_team") or {}
    home_form = await team_form(home)
    away_form = await team_form(away)
    return {
        "match": _fixture_payload(fixture, str(fixture.get("source_team_id") or home.get("id") or ""), saved),
        "comparison": {"home": home_form, "away": away_form},
    }


@router.get("/predictions")
async def saved_predictions(db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    rows = db.scalars(
        select(UserMatchPrediction)
        .where(UserMatchPrediction.user_id == user.id)
        .order_by(UserMatchPrediction.created_at.desc())
    ).all()
    provider = get_football_provider()
    hidden_incomplete = 0
    provider_checks = 0
    provider_limited = False
    now = datetime.now(timezone.utc)

    valid_rows = []
    for row in rows:
        has_real_teams = bool(
            row.home_team_name
            and row.away_team_name
            and row.home_team_name.strip().casefold() != "home"
            and row.away_team_name.strip().casefold() != "away"
        )
        kickoff = parse_utc(row.kickoff_utc)
        if not has_real_teams or kickoff is None:
            hidden_incomplete += 1
            continue
        valid_rows.append(row)

    # Oldest unresolved matches get checked first so newer picks cannot starve
    # finished matches when the provider-call budget is limited.
    unresolved = sorted(
        (
            row for row in valid_rows
            if row.result_status == "PENDING"
            and result_check_due(row.result_status, row.kickoff_utc, row.result_checked_at, now)
        ),
        key=lambda row: parse_utc(row.kickoff_utc) or now,
    )

    for row in unresolved[:3]:
        try:
            provider_checks += 1
            match = await provider.get_match(row.match_id)
            actual = actual_outcome(match)
            row.result_checked_at = now
            if actual:
                score = match.get("score") or {}
                row.actual_outcome = actual
                row.home_score = score.get("home")
                row.away_score = score.get("away")
                row.result_status = "CORRECT" if actual == row.predicted_outcome else "INCORRECT"
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                provider_limited = True
                break
        except httpx.HTTPError:
            continue

    if db.dirty:
        db.commit()

    predictions = []
    correct = 0
    scored = 0
    for row in valid_rows:
        if row.result_status in {"CORRECT", "INCORRECT"}:
            scored += 1
            correct += int(row.result_status == "CORRECT")
        score = None
        if row.home_score is not None and row.away_score is not None:
            score = {"home": row.home_score, "away": row.away_score}
        predictions.append({
            "id": row.id,
            "match_id": row.match_id,
            "home_team_name": row.home_team_name,
            "away_team_name": row.away_team_name,
            "predicted_outcome": row.predicted_outcome,
            "kickoff_utc": row.kickoff_utc,
            "created_at": row.created_at,
            "actual_outcome": row.actual_outcome,
            "result_status": row.result_status,
            "score": score,
        })

    notice = None
    if provider_limited:
        notice = "Live result refresh is temporarily paused because the football data provider rate limit was reached. Saved results remain available."
    elif unresolved and len(unresolved) > provider_checks:
        notice = f"Checked {provider_checks} pending prediction result{'s' if provider_checks != 1 else ''} this refresh. More eligible results will be checked on the next refresh."
    elif not scored:
        notice = "Accuracy will appear after one of your predicted matches finishes."

    return {
        "predictions": predictions,
        "total": len(predictions),
        "hidden_incomplete": hidden_incomplete,
        "scored": scored,
        "correct": correct,
        "accuracy_percent": round((correct / scored) * 100, 1) if scored else None,
        "notice": notice,
    }


@router.post("/{match_id}/prediction")
async def save_prediction(match_id: str, choice: PredictionChoice, db: Session = Depends(get_db)) -> dict:
    outcome = choice.outcome.upper()
    if outcome not in {"HOME", "DRAW", "AWAY"}:
        raise HTTPException(status_code=400, detail="Prediction must be HOME, DRAW, or AWAY.")
    user = _get_or_create_local_user(db)
    fixture = await _find_personalized_match(db, user, match_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="This match is not available in your personalized match feed.")
    kickoff = parse_utc(fixture.get("utc_date"))
    if kickoff is None:
        raise HTTPException(status_code=409, detail="This match does not have a valid kickoff time yet.")
    if kickoff <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Predictions are locked once the match kicks off.")
    home_name = (fixture.get("home_team") or {}).get("name") or "Home"
    away_name = (fixture.get("away_team") or {}).get("name") or "Away"
    kickoff_value = fixture.get("utc_date")
    existing = db.scalar(select(UserMatchPrediction).where(UserMatchPrediction.user_id == user.id, UserMatchPrediction.match_id == match_id))
    if existing:
        if existing.result_status != "PENDING":
            raise HTTPException(status_code=409, detail="This prediction has already been scored and can no longer be changed.")
        existing.predicted_outcome = outcome
        existing.home_team_name = home_name
        existing.away_team_name = away_name
        existing.kickoff_utc = kickoff_value
        existing.result_checked_at = None
        db.commit()
        return {"prediction": outcome, "xp_awarded": 0, "updated": True, "progress": progress_summary(db, user.id)}
    db.add(UserMatchPrediction(user_id=user.id, match_id=match_id, home_team_name=home_name, away_team_name=away_name, predicted_outcome=outcome, kickoff_utc=kickoff_value))
    db.add(XPEvent(user_id=user.id, amount=10, source_type="match_prediction", source_id=match_id))
    db.commit()
    return {"prediction": outcome, "xp_awarded": 10, "updated": False, "progress": progress_summary(db, user.id)}
