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

# V2 starter bank. Later this will be generated/validated from provider data and AI.
QUESTIONS = [
    {"id": "q1", "question": "How many players does a football team have on the field at kickoff?", "options": ["9", "10", "11", "12"], "answer": 2},
    {"id": "q2", "question": "Which position is allowed to handle the ball inside their own penalty area?", "options": ["Centre-back", "Goalkeeper", "Striker", "Winger"], "answer": 1},
    {"id": "q3", "question": "How long is a standard football match before added time?", "options": ["80 minutes", "90 minutes", "100 minutes", "120 minutes"], "answer": 1},
    {"id": "q4", "question": "What is awarded when a defending player commits a direct-free-kick foul inside their own penalty area?", "options": ["Corner kick", "Drop ball", "Penalty kick", "Throw-in"], "answer": 2},
    {"id": "q5", "question": "Which card sends a player off?", "options": ["Blue", "Green", "Red", "White"], "answer": 2},
]


class QuizSubmission(BaseModel):
    answers: list[int]


def quiz_id() -> str:
    return date.today().isoformat()


@router.get("/daily")
def daily_quiz(db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    event = db.scalar(select(XPEvent).where(XPEvent.user_id == user.id, XPEvent.source_type == "daily_quiz", XPEvent.source_id == quiz_id()))
    return {
        "quiz_id": quiz_id(),
        "title": "Daily Football Quiz",
        "questions": [{"id": q["id"], "question": q["question"], "options": q["options"]} for q in QUESTIONS],
        "completed": event is not None,
        "xp_available": 100,
    }


@router.post("/daily/submit")
def submit_daily_quiz(submission: QuizSubmission, db: Session = Depends(get_db)) -> dict:
    if len(submission.answers) != len(QUESTIONS):
        raise HTTPException(status_code=400, detail="Answer every question before submitting.")
    if any(answer < 0 or answer >= len(QUESTIONS[index]["options"]) for index, answer in enumerate(submission.answers)):
        raise HTTPException(status_code=400, detail="One or more quiz answers are invalid.")

    user = _get_or_create_local_user(db)
    correct = sum(answer == question["answer"] for answer, question in zip(submission.answers, QUESTIONS))
    score_percent = round((correct / len(QUESTIONS)) * 100)
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
        "total": len(QUESTIONS),
        "score_percent": score_percent,
        "xp_awarded": xp_awarded,
        "already_rewarded": existing is not None or xp_awarded == 0,
        "correct_answers": [question["answer"] for question in QUESTIONS],
        "progress": progress_summary(db, user.id),
    }
