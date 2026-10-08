from app.api.auth import require_user
import httpx
from fastapi import Request, APIRouter, Depends, HTTPException, status
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
def get_profile(request: Request, db: Session = Depends(get_db)) -> dict:
    user = require_user(request, db)
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
async def get_club_pulse(request: Request, db: Session = Depends(get_db)) -> dict:
    """Personalized club facts; never fabricate unavailable provider data."""
    user = require_user(request, db)
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
            ("recent", lambda tid: provider.get_recent_results(tid, limit=5)),
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
            "recent_form": [
                (
                    "D" if match["score"]["home"] == match["score"]["away"]
                    else "W" if (
                        (str(match["home_team"]["id"]) == str(team.provider_id) and match["score"]["home"] > match["score"]["away"])
                        or (str(match["away_team"]["id"]) == str(team.provider_id) and match["score"]["away"] > match["score"]["home"])
                    ) else "L"
                )
                for match in recent[-5:]
                if match.get("score")
                and match["score"].get("home") is not None
                and match["score"].get("away") is not None
                and (str(match["home_team"]["id"]) == str(team.provider_id) or str(match["away_team"]["id"]) == str(team.provider_id))
            ],
            "unavailable": unavailable,
        })
    return {"clubs": clubs, "count": len(clubs)}


@router.get("/achievements")
def get_achievements(request: Request, db: Session = Depends(get_db)) -> dict:
    user = require_user(request, db)
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
        ("quiz_veteran", "Quiz Veteran", "Complete 15 rewarded Daily Quizzes", quiz_completions >= 15, min(quiz_completions, 15), 15),
        ("quiz_legend", "Quiz Legend", "Complete 30 rewarded Daily Quizzes", quiz_completions >= 30, min(quiz_completions, 30), 30),
        ("week_warrior", "Week Warrior", "Reach a 7-day activity streak", progress["longest_streak"] >= 7, min(progress["longest_streak"], 7), 7),
        ("streak_champion", "Streak Champion", "Reach a 14-day activity streak", progress["longest_streak"] >= 14, min(progress["longest_streak"], 14), 14),
        ("unstoppable", "Unstoppable", "Reach a 30-day activity streak", progress["longest_streak"] >= 30, min(progress["longest_streak"], 30), 30),
        ("match_scout", "Match Scout", "Make 10 match predictions", predictions >= 10, min(predictions, 10), 10),
        ("prediction_pro", "Prediction Pro", "Make 25 match predictions", predictions >= 25, min(predictions, 25), 25),
        ("prediction_legend", "Prediction Legend", "Make 50 match predictions", predictions >= 50, min(predictions, 50), 50),
        ("sharp_eye", "Sharp Eye", "Get 5 scored match predictions correct", correct >= 5, min(correct, 5), 5),
        ("oracle", "Oracle", "Get 20 scored match predictions correct", correct >= 20, min(correct, 20), 20),
        ("xp_1000", "1K Club", "Earn 1,000 lifetime XP", progress["total_xp"] >= 1000, min(progress["total_xp"], 1000), 1000),
        ("xp_2500", "2.5K Club", "Earn 2,500 lifetime XP", progress["total_xp"] >= 2500, min(progress["total_xp"], 2500), 2500),
        ("xp_5000", "5K Club", "Earn 5,000 lifetime XP", progress["total_xp"] >= 5000, min(progress["total_xp"], 5000), 5000),
    ]
    achievements = [{"id": key, "name": name, "description": description, "unlocked": unlocked, "progress": value, "target": target} for key, name, description, unlocked, value, target in definitions]
    return {"progress": progress, "stats": stats, "analysis_access": analysis_access_summary(db, user.id), "achievements": achievements, "unlocked": sum(1 for item in achievements if item["unlocked"]), "total": len(achievements)}


@router.put("/primary-team")
async def set_primary_team(choice: TeamChoice, request: Request, db: Session = Depends(get_db)) -> dict:
    user = require_user(request, db)
    team = await _get_or_create_team(db, choice.provider_team_id)
    user.primary_team_id = team.id
    db.commit()
    db.refresh(user)
    return {"primary_team": _team_payload(team)}


@router.post("/favorites", status_code=status.HTTP_201_CREATED)
async def add_favorite(choice: TeamChoice, request: Request, db: Session = Depends(get_db)) -> dict:
    user = require_user(request, db)
    team = await _get_or_create_team(db, choice.provider_team_id)
    existing = db.scalar(select(UserFavoriteTeam).where(UserFavoriteTeam.user_id == user.id, UserFavoriteTeam.team_id == team.id))
    if not existing:
        db.add(UserFavoriteTeam(user_id=user.id, team_id=team.id))
        db.commit()
    return {"favorite": _team_payload(team)}


@router.delete("/favorites/{provider_team_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(provider_team_id: str, request: Request, db: Session = Depends(get_db)) -> None:
    user = require_user(request, db)
    team = db.scalar(select(Team).where(Team.provider_id == provider_team_id))
    if not team:
        raise HTTPException(status_code=404, detail="Favorite team not found.")
    link = db.scalar(select(UserFavoriteTeam).where(UserFavoriteTeam.user_id == user.id, UserFavoriteTeam.team_id == team.id))
    if not link:
        raise HTTPException(status_code=404, detail="Favorite team not found.")
    db.delete(link)
    db.commit()
