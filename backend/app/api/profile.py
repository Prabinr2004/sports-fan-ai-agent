from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.team import Team
from app.models.user import User, UserFavoriteTeam
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
