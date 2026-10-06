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

router = APIRouter(prefix="/matches", tags=["matches"])


class PredictionChoice(BaseModel):
    outcome: str


def _parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _actual_outcome(match: dict) -> str | None:
    if match.get("status") != "FINISHED":
        return None
    score = match.get("score") or {}
    home, away = score.get("home"), score.get("away")
    if home is None or away is None:
        return None
    if home > away:
        return "HOME"
    if away > home:
        return "AWAY"
    return "DRAW"


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
    kickoff = _parse_utc(fixture.get("utc_date"))
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


@router.get("/predictions")
async def saved_predictions(db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    rows = db.scalars(select(UserMatchPrediction).where(UserMatchPrediction.user_id == user.id).order_by(UserMatchPrediction.created_at.desc())).all()
    provider = get_football_provider()
    predictions = []
    correct = 0
    scored = 0
    provider_checks = 0
    provider_limited = False

    for row in rows:
        actual = None
        status = "PENDING"
        score = None
        kickoff = _parse_utc(row.kickoff_utc)
        # Upcoming matches cannot have a result yet, so never spend an API call on them.
        should_check_result = bool(kickoff and kickoff <= datetime.now(timezone.utc) and provider_checks < 3 and not provider_limited)
        if should_check_result:
            try:
                provider_checks += 1
                match = await provider.get_match(row.match_id)
                actual = _actual_outcome(match)
                if actual:
                    scored += 1
                    is_correct = actual == row.predicted_outcome
                    correct += int(is_correct)
                    status = "CORRECT" if is_correct else "INCORRECT"
                    score = match.get("score")
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    provider_limited = True
            except httpx.HTTPError:
                pass
        predictions.append({"id": row.id, "match_id": row.match_id, "home_team_name": row.home_team_name, "away_team_name": row.away_team_name, "predicted_outcome": row.predicted_outcome, "kickoff_utc": row.kickoff_utc, "created_at": row.created_at, "actual_outcome": actual, "result_status": status, "score": score})

    notice = None
    if provider_limited:
        notice = "Live result refresh is temporarily paused because the football data provider rate limit was reached. Your saved predictions are still available."
    elif not scored:
        notice = "Accuracy will appear after one of your predicted matches finishes."
    return {"predictions": predictions, "total": len(rows), "scored": scored, "correct": correct, "accuracy_percent": round((correct / scored) * 100, 1) if scored else None, "notice": notice}


@router.post("/{match_id}/prediction")
async def save_prediction(match_id: str, choice: PredictionChoice, db: Session = Depends(get_db)) -> dict:
    outcome = choice.outcome.upper()
    if outcome not in {"HOME", "DRAW", "AWAY"}:
        raise HTTPException(status_code=400, detail="Prediction must be HOME, DRAW, or AWAY.")
    user = _get_or_create_local_user(db)
    fixture = await _find_personalized_match(db, user, match_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="This match is not available in your personalized match feed.")
    kickoff = _parse_utc(fixture.get("utc_date"))
    if kickoff is None:
        raise HTTPException(status_code=409, detail="This match does not have a valid kickoff time yet.")
    if kickoff <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Predictions are locked once the match kicks off.")
    home_name = (fixture.get("home_team") or {}).get("name") or "Home"
    away_name = (fixture.get("away_team") or {}).get("name") or "Away"
    kickoff_value = fixture.get("utc_date")
    existing = db.scalar(select(UserMatchPrediction).where(UserMatchPrediction.user_id == user.id, UserMatchPrediction.match_id == match_id))
    if existing:
        existing.predicted_outcome = outcome
        existing.home_team_name = home_name
        existing.away_team_name = away_name
        existing.kickoff_utc = kickoff_value
        db.commit()
        return {"prediction": outcome, "xp_awarded": 0, "updated": True, "progress": progress_summary(db, user.id)}
    db.add(UserMatchPrediction(user_id=user.id, match_id=match_id, home_team_name=home_name, away_team_name=away_name, predicted_outcome=outcome, kickoff_utc=kickoff_value))
    db.add(XPEvent(user_id=user.id, amount=10, source_type="match_prediction", source_id=match_id))
    db.commit()
    return {"prediction": outcome, "xp_awarded": 10, "updated": False, "progress": progress_summary(db, user.id)}
