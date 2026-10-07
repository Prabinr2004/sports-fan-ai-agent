import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.progress import XPEvent
from app.models.prediction import UserMatchPrediction
from app.models.team import Team
from app.models.user import User, UserFavoriteTeam
from app.services.analysis_access import analysis_access_summary
from app.services.football import get_football_provider
from app.services.progress import progress_summary

router = APIRouter(prefix="/profile", tags=["profile"])

DEMO_EMAIL = "local@fansphere.dev"


class TeamChoice(BaseModel):
    provider_team_id: str


def _team_payload(team: Team | None) -> dict | None:
    if team is None:
        return None
    return {
        "id": team.id,
        "provider_id": team.provider_id,
        "name": team.name,
        "short_name": team.short_name,
        "country": team.country,
        "league_name": team.league_name,
        "crest_url": team.logo_url,
    }


def _get_or_create_local_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user:
        return user
    user = User(email=DEMO_EMAIL, display_name="Prabin", password_hash="local-development")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


async def _get_or_create_team(db: Session, provider_team_id: str) -> Team:
    team = db.scalar(select(Team).where(Team.provider_id == provider_team_id))
    if team:
        return team
    provider = get_football_provider()
    remote = await provider.get_team(provider_team_id)
    team = Team(
        provider_id=provider_team_id,
        name=remote.get("name") or "Unknown team",
        short_name=remote.get("short_name"),
        country=remote.get("country"),
        league_name=remote.get("league_name"),
        logo_url=remote.get("crest_url"),
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.get("")
def get_profile(db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    favorite_links = db.scalars(select(UserFavoriteTeam).where(UserFavoriteTeam.user_id == user.id)).all()
    favorites = []
    for link in favorite_links:
        team = db.get(Team, link.team_id)
        if team:
            favorites.append(_team_payload(team))
    return {
        "id": user.id,
        "display_name": user.display_name,
        "primary_team": _team_payload(user.primary_team),
        "favorites": favorites,
        "progress": progress_summary(db, user.id),
        "mode": "local-development",
    }



@router.get("/club-pulse")
async def get_club_pulse(db: Session = Depends(get_db)) -> dict:
    """Personalized club facts; never fabricate unavailable provider data."""
    user = _get_or_create_local_user(db)
    saved = []
    if user.primary_team:
        saved.append((user.primary_team, True))
    for link in db.scalars(select(UserFavoriteTeam).where(UserFavoriteTeam.user_id == user.id)).all():
        team = db.get(Team, link.team_id)
        if team and all(t.provider_id != team.provider_id for t, _ in saved):
            saved.append((team, False))
    provider = get_football_provider()
    clubs = []
    for team, primary in saved[:6]:
        results = {}
        unavailable = []
        for label, method in (
            ("fixtures", provider.get_fixtures),
            ("standings", provider.get_team_standings),
            ("scorers", provider.get_team_scorers),
            ("recent", lambda tid: provider.get_recent_results(tid, limit=1)),
        ):
            try:
                results[label] = await method(team.provider_id)
            except (httpx.HTTPError, HTTPException):
                results[label] = []
                unavailable.append(label)
        standings = results["standings"]
        scorers = results["scorers"]
        recent = results["recent"]
        fixtures = sorted(results["fixtures"], key=lambda m: m.get("utc_date") or "")
        clubs.append({
            "team": _team_payload(team),
            "is_primary": primary,
            "next_match": fixtures[0] if fixtures else None,
            "standing": next((s for s in standings if s.get("type") == "TOTAL"), standings[0] if standings else None),
            "top_scorer": max(scorers, key=lambda s: s.get("goals") or 0) if scorers else None,
            "latest_result": recent[-1] if recent else None,
            "unavailable": unavailable,
        })
    return {"clubs": clubs, "count": len(clubs)}


@router.get("/achievements")
def get_achievements(db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    progress = progress_summary(db, user.id)
    quiz_completions = int(db.scalar(select(func.count(XPEvent.id)).where(XPEvent.user_id == user.id, XPEvent.source_type == "daily_quiz")) or 0)
    predictions = int(db.scalar(select(func.count(UserMatchPrediction.id)).where(UserMatchPrediction.user_id == user.id)) or 0)
    scored = int(db.scalar(select(func.count(UserMatchPrediction.id)).where(UserMatchPrediction.user_id == user.id, UserMatchPrediction.result_status.in_(["CORRECT", "INCORRECT"]))) or 0)
    correct = int(db.scalar(select(func.count(UserMatchPrediction.id)).where(UserMatchPrediction.user_id == user.id, UserMatchPrediction.result_status == "CORRECT")) or 0)
    stats = {"quiz_completions": quiz_completions, "predictions": predictions, "scored_predictions": scored, "correct_predictions": correct}
    definitions = [
        ("first_steps", "First Steps", "Earn your first XP", progress["total_xp"] >= 1, min(progress["total_xp"], 1), 1),
        ("quiz_rookie", "Quiz Rookie", "Complete your first rewarded Daily Quiz", quiz_completions >= 1, min(quiz_completions, 1), 1),
        ("quiz_regular", "Quiz Regular", "Complete 5 rewarded Daily Quizzes", quiz_completions >= 5, min(quiz_completions, 5), 5),
        ("on_fire", "On Fire", "Reach a 3-day activity streak", progress["longest_streak"] >= 3, min(progress["longest_streak"], 3), 3),
        ("fan_predictor", "Fan Predictor", "Make 5 match predictions", predictions >= 5, min(predictions, 5), 5),
        ("called_it", "Called It", "Get a scored match prediction correct", correct >= 1, min(correct, 1), 1),
        ("xp_500", "500 Club", "Earn 500 total XP", progress["total_xp"] >= 500, min(progress["total_xp"], 500), 500),
    ]
    achievements = [{"id": key, "name": name, "description": description, "unlocked": unlocked, "progress": value, "target": target} for key, name, description, unlocked, value, target in definitions]
    return {"progress": progress, "stats": stats, "analysis_access": analysis_access_summary(db, user.id), "achievements": achievements, "unlocked": sum(1 for item in achievements if item["unlocked"]), "total": len(achievements)}


@router.put("/primary-team")
async def set_primary_team(choice: TeamChoice, db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    team = await _get_or_create_team(db, choice.provider_team_id)
    user.primary_team_id = team.id
    db.commit()
    db.refresh(user)
    return {"primary_team": _team_payload(team)}


@router.post("/favorites", status_code=status.HTTP_201_CREATED)
async def add_favorite(choice: TeamChoice, db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    team = await _get_or_create_team(db, choice.provider_team_id)
    existing = db.scalar(select(UserFavoriteTeam).where(UserFavoriteTeam.user_id == user.id, UserFavoriteTeam.team_id == team.id))
    if not existing:
        db.add(UserFavoriteTeam(user_id=user.id, team_id=team.id))
        db.commit()
    return {"favorite": _team_payload(team)}


@router.delete("/favorites/{provider_team_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(provider_team_id: str, db: Session = Depends(get_db)) -> None:
    user = _get_or_create_local_user(db)
    team = db.scalar(select(Team).where(Team.provider_id == provider_team_id))
    if not team:
        raise HTTPException(status_code=404, detail="Favorite team not found.")
    link = db.scalar(select(UserFavoriteTeam).where(UserFavoriteTeam.user_id == user.id, UserFavoriteTeam.team_id == team.id))
    if not link:
        raise HTTPException(status_code=404, detail="Favorite team not found.")
    db.delete(link)
    db.commit()
