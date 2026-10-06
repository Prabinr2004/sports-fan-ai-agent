from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.profile import _get_or_create_local_user
from app.database.session import get_db
from app.models.progress import XPEvent
from app.services.progress import progress_summary, record_activity_day

router = APIRouter(prefix="/quiz", tags=["quiz"])

GENERAL_QUESTIONS = [
    {"id": "general-1", "question": "How many players does a football team have on the field at kickoff?", "options": ["9", "10", "11", "12"], "answer": 2},
    {"id": "general-2", "question": "Which position is allowed to handle the ball inside their own penalty area?", "options": ["Centre-back", "Goalkeeper", "Striker", "Winger"], "answer": 1},
    {"id": "general-3", "question": "How long is a standard football match before added time?", "options": ["80 minutes", "90 minutes", "100 minutes", "120 minutes"], "answer": 1},
    {"id": "general-4", "question": "What is awarded when a defending player commits a direct-free-kick foul inside their own penalty area?", "options": ["Corner kick", "Drop ball", "Penalty kick", "Throw-in"], "answer": 2},
    {"id": "general-5", "question": "Which card sends a player off?", "options": ["Blue", "Green", "Red", "White"], "answer": 2},
]

QUIZ_LEVELS = {
    1: {"theme": "Football Basics", "description": "General football rules and knowledge."},
    2: {"theme": "Know Your Club", "description": "Basic facts about your primary team."},
    3: {"theme": "Players & Legends", "description": "Current players, club icons, and legends."},
    4: {"theme": "Club History", "description": "History, trophies, rivalries, and important eras."},
    5: {"theme": "Expert Mode", "description": "Matches, seasons, records, tactics, and advanced club knowledge."},
}


class QuizSubmission(BaseModel):
    answers: list[int]


def quiz_id() -> str:
    return date.today().isoformat()


def quiz_level_from_completions(completions: int) -> int:
    # A level lasts five rewarded daily quizzes. Level 5 is the ongoing expert tier.
    return min(5, completions // 5 + 1)


def rewarded_quiz_completions(db: Session, user_id: int) -> int:
    return len(list(db.scalars(select(XPEvent.id).where(XPEvent.user_id == user_id, XPEvent.source_type == "daily_quiz")).all()))


def quiz_context(db: Session, user) -> dict:
    completions = rewarded_quiz_completions(db, user.id)
    level = quiz_level_from_completions(completions)
    team = user.primary_team
    # Team-specific generation is introduced after Level 1. Until the grounded
    # team question builder is available, never invent club facts.
    effective_level = level if level == 1 or team is not None else 1
    meta = QUIZ_LEVELS[effective_level]
    return {
        "level": effective_level,
        "unlocked_level": level,
        "theme": meta["theme"],
        "description": meta["description"],
        "team": {"id": team.provider_id, "name": team.name} if team else None,
        "days_to_next_level": max(0, 5 - (completions % 5)) if level < 5 else 0,
    }


@router.get("/daily")
def daily_quiz(db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    event = db.scalar(select(XPEvent).where(XPEvent.user_id == user.id, XPEvent.source_type == "daily_quiz", XPEvent.source_id == quiz_id()))
    context = quiz_context(db, user)

    # Level 1 is live now. Higher-level question builders will use grounded
    # primary-team data rather than sharing generic or hallucinated questions.
    questions = GENERAL_QUESTIONS
    return {
        "quiz_id": quiz_id(),
        "title": context["theme"],
        "questions": [{"id": q["id"], "question": q["question"], "options": q["options"]} for q in questions],
        "completed": event is not None,
        "xp_available": 100,
        "quiz_level": context["level"],
        "unlocked_level": context["unlocked_level"],
        "theme": context["theme"],
        "description": context["description"],
        "team": context["team"],
        "days_to_next_level": context["days_to_next_level"],
    }


@router.post("/daily/submit")
def submit_daily_quiz(submission: QuizSubmission, db: Session = Depends(get_db)) -> dict:
    questions = GENERAL_QUESTIONS
    if len(submission.answers) != len(questions):
        raise HTTPException(status_code=400, detail="Answer every question before submitting.")
    if any(answer < 0 or answer >= len(questions[index]["options"]) for index, answer in enumerate(submission.answers)):
        raise HTTPException(status_code=400, detail="One or more quiz answers are invalid.")

    user = _get_or_create_local_user(db)
    correct = sum(answer == question["answer"] for answer, question in zip(submission.answers, questions))
    score_percent = round((correct / len(questions)) * 100)
    source_id = quiz_id()
    existing = db.scalar(select(XPEvent).where(XPEvent.user_id == user.id, XPEvent.source_type == "daily_quiz", XPEvent.source_id == source_id))
    xp_awarded = 0

    if not existing:
        xp_awarded = 50 + correct * 10
        db.add(XPEvent(user_id=user.id, amount=xp_awarded, source_type="daily_quiz", source_id=source_id))
        record_activity_day(db, user.id)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            xp_awarded = 0

    return {
        "quiz_id": source_id,
        "correct": correct,
        "total": len(questions),
        "score_percent": score_percent,
        "xp_awarded": xp_awarded,
        "already_rewarded": existing is not None or xp_awarded == 0,
        "correct_answers": [question["answer"] for question in questions],
        "quiz": quiz_context(db, user),
        "progress": progress_summary(db, user.id),
    }
