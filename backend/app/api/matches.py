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
    home_team_name: str | None = None
    away_team_name: str | None = None
    kickoff_utc: str | None = None


def _fixture_payload(fixture: dict, provider_team_id: str, saved: UserMatchPrediction | None = None) -> dict:
    return {
        **fixture,
        "source_team_id": provider_team_id,
        "user_prediction": saved.predicted_outcome if saved else None,
    }


@router.get("")
async def personalized_matches(db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    team_ids: list[str] = []
    if user.primary_team:
        team_ids.append(user.primary_team.provider_id)
    links = db.scalars(select(UserFavoriteTeam).where(UserFavoriteTeam.user_id == user.id)).all()
    for link in links:
        team = db.get(Team, link.team_id)
        if team and team.provider_id not in team_ids:
            team_ids.append(team.provider_id)

    if not team_ids:
        return {"matches": [], "notice": "Choose a primary team or follow teams to build your match feed."}

    provider = get_football_provider()
    collected: dict[str, dict] = {}
    unavailable = 0
    for provider_team_id in team_ids[:6]:
        try:
            fixtures = await provider.get_fixtures(provider_team_id)
        except Exception:
            unavailable += 1
            continue
        for fixture in fixtures:
            match_id = str(fixture.get("id"))
            if match_id and match_id not in collected:
                saved = db.scalar(select(UserMatchPrediction).where(UserMatchPrediction.user_id == user.id, UserMatchPrediction.match_id == match_id))
                collected[match_id] = _fixture_payload(fixture, provider_team_id, saved)

    matches = sorted(collected.values(), key=lambda match: match.get("utc_date") or "")
    notice = None
    if unavailable:
        notice = "Some followed-team fixtures are unavailable on the current football data plan."
    return {"matches": matches[:30], "notice": notice}


@router.get("/predictions")
def saved_predictions(db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    rows = db.scalars(
        select(UserMatchPrediction)
        .where(UserMatchPrediction.user_id == user.id)
        .order_by(UserMatchPrediction.created_at.desc())
    ).all()
    return {
        "predictions": [
            {
                "id": row.id,
                "match_id": row.match_id,
                "home_team_name": row.home_team_name,
                "away_team_name": row.away_team_name,
                "predicted_outcome": row.predicted_outcome,
                "kickoff_utc": row.kickoff_utc,
                "created_at": row.created_at,
            }
            for row in rows
        ],
        "total": len(rows),
        "notice": "Prediction scoring and accuracy will activate when completed-match results are connected.",
    }


@router.post("/{match_id}/prediction")
def save_prediction(match_id: str, choice: PredictionChoice, db: Session = Depends(get_db)) -> dict:
    outcome = choice.outcome.upper()
    if outcome not in {"HOME", "DRAW", "AWAY"}:
        raise HTTPException(status_code=400, detail="Prediction must be HOME, DRAW, or AWAY.")

    user = _get_or_create_local_user(db)
    existing = db.scalar(select(UserMatchPrediction).where(UserMatchPrediction.user_id == user.id, UserMatchPrediction.match_id == match_id))
    if existing:
        existing.predicted_outcome = outcome
        if choice.home_team_name:
            existing.home_team_name = choice.home_team_name
        if choice.away_team_name:
            existing.away_team_name = choice.away_team_name
        if choice.kickoff_utc:
            existing.kickoff_utc = choice.kickoff_utc
        db.commit()
        return {"prediction": outcome, "xp_awarded": 0, "updated": True, "progress": progress_summary(db, user.id)}

    prediction = UserMatchPrediction(
        user_id=user.id,
        match_id=match_id,
        home_team_name=choice.home_team_name or "Home",
        away_team_name=choice.away_team_name or "Away",
        predicted_outcome=outcome,
        kickoff_utc=choice.kickoff_utc,
    )
    db.add(prediction)
    xp_event = XPEvent(user_id=user.id, amount=10, source_type="match_prediction", source_id=match_id)
    db.add(xp_event)
    db.commit()
    return {"prediction": outcome, "xp_awarded": 10, "updated": False, "progress": progress_summary(db, user.id)}
