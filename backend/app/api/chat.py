"""Authenticated FanSphere AI chat. Read-only context; no football provider calls."""
import json
import httpx
from sqlalchemy import select, func
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import require_user
from app.core.config import settings
from app.database.session import get_db
from app.models.user import User
from app.services.progress import progress_summary
from app.services.gems import gem_balance, spendable_xp, XP_PER_GEM, GEMS_PER_ANALYSIS
from app.models.quiz import QuizRoundCompletion
from app.models.prediction import UserMatchPrediction
from app.services.quiz_progression import MAX_LEVEL, ROUNDS_PER_LEVEL, ROUNDS_TO_UNLOCK, unlocked_level, level_progress

router = APIRouter(prefix="/chat", tags=["assistant"])


class Message(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[Message] = Field(default_factory=list, max_length=12)



TOOLS = [
    {"type":"function","function":{"name":"get_wallet","description":"Get the authenticated fan's real XP, Gems, level and streak.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"get_quiz_progress","description":"Get rewarded quiz level and completed rounds for this fan.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"get_saved_predictions","description":"Get this fan's saved match picks and known results, not live scores.","parameters":{"type":"object","properties":{}}}},
]

def read_tool(name: str, db: Session, user_id: int) -> dict:
    if name == "get_wallet":
        return {**progress_summary(db,user_id),"gems":gem_balance(db,user_id),
                "spendable_xp":spendable_xp(db,user_id),"xp_per_gem":XP_PER_GEM,
                "gems_per_extra_analysis":GEMS_PER_ANALYSIS,
                "lifetime_xp_is_not_spent":True}
    if name == "get_quiz_progress":
        rows=db.scalars(select(QuizRoundCompletion).where(QuizRoundCompletion.user_id==user_id)).all()
        counts={i:sum(row.level==i for row in rows) for i in range(1,MAX_LEVEL+1)}
        highest=unlocked_level(counts)
        return {"highest_unlocked_level":highest,"rounds_per_level":ROUNDS_PER_LEVEL,
                "rounds_to_unlock":ROUNDS_TO_UNLOCK,
                "levels":[level_progress(i,counts,highest) for i in range(1,MAX_LEVEL+1)],
                "daily_rewarded_attempt_limit":1}
    if name == "get_saved_predictions":
        rows=db.scalars(select(UserMatchPrediction).where(UserMatchPrediction.user_id==user_id)
                        .order_by(UserMatchPrediction.id.desc()).limit(10)).all()
        total=db.scalar(select(func.count()).select_from(UserMatchPrediction)
                        .where(UserMatchPrediction.user_id==user_id)) or 0
        return {"total_saved_picks":total,"recent_picks":[
                {"home":p.home_team_name,"away":p.away_team_name,"pick":p.predicted_outcome,
                 "status":p.result_status,"actual_outcome":p.actual_outcome}
                for p in rows],"live_data_available":False}
    return {"error":"Unsupported tool"}

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
        "Use your read-only wallet, quiz and saved-prediction tools for personalized questions; acknowledge when information may be outdated. "
        "Do not invent a user's private stats or assert match probabilities without provided data. "
        "You cannot award XP, generate official quiz rounds, place picks, spend Gems or unlock analyses via chat. "
        f"Authenticated fan: {user.display_name}. Primary club: {club}. "
        f"Lifetime XP: {progress.get('total_xp', 0)}. Current streak: {progress.get('current_streak', 0)} days. "
        "Keep answers concise and practical."
    )
    messages = [{"role": "system", "content": system}]
    messages += [{"role": m.role, "content": m.content} for m in payload.history[-10:] if m.role in ("user", "assistant")]
    messages.append({"role": "user", "content": payload.message})

    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            headers={"Authorization":f"Bearer {settings.openrouter_api_key}","Content-Type":"application/json"}
            response=await client.post("https://openrouter.ai/api/v1/chat/completions",
                headers=headers,json={"model":"openai/gpt-4o-mini","messages":messages,
                "tools":TOOLS,"tool_choice":"auto","max_tokens":650,"temperature":0.3})
            response.raise_for_status()
            assistant=response.json()["choices"][0]["message"]
            calls=assistant.get("tool_calls") or []
            if calls:
                # One bounded read-only tool round; no provider calls or database writes.
                selected=calls[:3]
                messages.append({"role":"assistant","content":assistant.get("content"),"tool_calls":selected})
                for call in selected:
                    result=read_tool(call.get("function",{}).get("name",""),db,user.id)
                    messages.append({"role":"tool","tool_call_id":call["id"],"content":json.dumps(result)})
                response=await client.post("https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,json={"model":"openai/gpt-4o-mini","messages":messages,
                    "max_tokens":650,"temperature":0.3})
                response.raise_for_status()
            answer=response.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError,KeyError,IndexError,TypeError,ValueError) as exc:
        raise HTTPException(status_code=502,detail="The AI assistant is temporarily unavailable. Please try again.") from exc
    if not isinstance(answer, str) or not answer.strip():
        raise HTTPException(status_code=502, detail="The AI assistant returned an empty response.")
    return {"reply": answer.strip()}
