"""Authenticated FanSphere AI chat. Read-only context; no football provider calls."""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import require_user
from app.core.config import settings
from app.database.session import get_db
from app.models.user import User
from app.services.progress import progress_summary

router = APIRouter(prefix="/chat", tags=["assistant"])


class Message(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[Message] = Field(default_factory=list, max_length=12)


@router.post("")
async def chat(payload: ChatRequest, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    if not settings.openrouter_api_key:
        raise HTTPException(status_code=503, detail="AI Assistant is not configured. Set OPENROUTER_API_KEY in the backend environment.")
    progress = progress_summary(db, user.id)
    club = user.primary_team.name if user.primary_team else "not selected"
    system = (
        "You are FanSphere AI, a helpful, friendly football fan assistant inside FanSphere V2. "
        "Help with football knowledge and navigating the app: Home, My Team, Favorites, Matches, "
        "Predictions, Daily Quiz, Leaderboard, Wallet, Profile and AI Assistant. "
        "Explain that Daily Quiz has one rewarded attempt per day, and predictions are fan picks for XP, not gambling. "
        "Never claim to have accessed live scores, fixtures, player transfers, or changed user data. "
        "You have no external football tools in this version; acknowledge when information may be outdated. "
        "Do not invent a user's private stats or assert match probabilities without provided data. "
        "You cannot award XP, generate official quiz rounds, place picks, or unlock analyses via chat. "
        f"Authenticated fan: {user.display_name}. Primary club: {club}. "
        f"Lifetime XP: {progress.get('total_xp', 0)}. Current streak: {progress.get('current_streak', 0)} days. "
        "Keep answers concise and practical."
    )
    messages = [{"role": "system", "content": system}]
    messages += [{"role": m.role, "content": m.content} for m in payload.history[-10:] if m.role in ("user", "assistant")]
    messages.append({"role": "user", "content": payload.message})
    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}", "Content-Type": "application/json"},
                json={"model": "openai/gpt-4o-mini", "messages": messages, "max_tokens": 550, "temperature": 0.5},
            )
            response.raise_for_status()
            answer = response.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="The AI assistant is temporarily unavailable. Please try again.") from exc
    if not isinstance(answer, str) or not answer.strip():
        raise HTTPException(status_code=502, detail="The AI assistant returned an empty response.")
    return {"reply": answer.strip()}
