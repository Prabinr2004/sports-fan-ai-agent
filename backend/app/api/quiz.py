from app.api.auth import require_user
from datetime import date
import json
import random

from fastapi import Request, APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.profile import _get_or_create_local_user
from app.database.session import get_db
from app.models.progress import XPEvent
from app.models.quiz import DailyQuizSnapshot
from app.services.analysis_access import grant_quiz_token
from app.services.progress import progress_summary, record_activity_day
from app.services.quiz_questions import build_team_questions

router = APIRouter(prefix="/quiz", tags=["quiz"])

GENERAL_QUESTIONS = [
    {"id": "general-1", "question": "How many players does a football team have on the field at kickoff?", "options": ["9", "10", "11", "12"], "answer": 2},
    {"id": "general-2", "question": "Which position is allowed to handle the ball inside their own penalty area?", "options": ["Centre-back", "Goalkeeper", "Striker", "Winger"], "answer": 1},
    {"id": "general-3", "question": "How long is a standard football match before added time?", "options": ["80 minutes", "90 minutes", "100 minutes", "120 minutes"], "answer": 1},
    {"id": "general-4", "question": "What is awarded when a defending player commits a direct-free-kick foul inside their own penalty area?", "options": ["Corner kick", "Drop ball", "Penalty kick", "Throw-in"], "answer": 2},
    {"id": "general-5", "question": "Which card sends a player off?", "options": ["Blue", "Green", "Red", "White"], "answer": 2},
    {"id": "general-6", "question": "What restart is awarded when the ball fully crosses the touchline?", "options": ["Corner kick", "Throw-in", "Penalty kick", "Goal kick"], "answer": 1},
    {"id": "general-7", "question": "How many halves are played in a standard football match?", "options": ["1", "2", "3", "4"], "answer": 1},
    {"id": "general-8", "question": "What is a hat-trick?", "options": ["Three goals by one player", "Three assists by one player", "Three yellow cards", "Three substitutions"], "answer": 0},
    {"id": "general-9", "question": "Which body part may an outfield player not deliberately use to control the ball?", "options": ["Head", "Chest", "Foot", "Hand"], "answer": 3},
    {"id": "general-10", "question": "Where is a corner kick taken from?", "options": ["Centre circle", "Penalty spot", "Corner arc", "Goal area"], "answer": 2},
    {"id": "general-11", "question": "What does a yellow card normally represent?", "options": ["A caution", "A goal", "A substitution", "Full-time"], "answer": 0},
    {"id": "general-12", "question": "Which official primarily enforces the Laws of the Game on the field?", "options": ["Captain", "Coach", "Referee", "Fourth substitute"], "answer": 2},
    {"id": "general-13", "question": "What happens when the score is level in a league match that allows draws?", "options": ["Home team wins", "Away team wins", "Match is a draw", "Penalty shootout"], "answer": 2},
    {"id": "general-14", "question": "How many points does a team normally receive for a league win?", "options": ["1", "2", "3", "4"], "answer": 2},
    {"id": "general-15", "question": "How many points does a team normally receive for a league draw?", "options": ["0", "1", "2", "3"], "answer": 1},
    {"id": "general-16", "question": "Which restart begins each half?", "options": ["Throw-in", "Kick-off", "Corner kick", "Goal kick"], "answer": 1},
    {"id": "general-17", "question": "What is added time intended to compensate for?", "options": ["Time lost during play", "Half-time", "Warm-ups", "Travel time"], "answer": 0},
    {"id": "general-18", "question": "Which line must the whole ball cross for a goal to be scored?", "options": ["Touchline", "Halfway line", "Goal line between the posts", "Penalty-area line"], "answer": 2},
    {"id": "general-19", "question": "Who usually wears a different-colored kit from their teammates?", "options": ["Goalkeeper", "Captain", "Striker", "Left-back"], "answer": 0},
    {"id": "general-20", "question": "What is the area around the penalty spot called?", "options": ["Centre circle", "Technical area", "Penalty area", "Corner arc"], "answer": 2},
]

GENERAL_QUESTIONS.extend([
    {"id": "general-21", "question": "What is an offside position judged against?", "options": ["The ball and second-last opponent","The referee","The halfway line only","The goalkeeper only"], "answer": 0},
    {"id": "general-22", "question": "What is the maximum number of players on the field for one team during normal play?", "options": ["9","10","11","12"], "answer": 2},
    {"id": "general-23", "question": "What does VAR stand for?", "options": ["Video Assistant Referee","Virtual Action Replay","Verified Assistant Rules","Video Action Review"], "answer": 0},
    {"id": "general-24", "question": "Which restart follows when an attacker last touches the ball over the defending team's goal line without a goal?", "options": ["Throw-in","Goal kick","Corner kick","Penalty kick"], "answer": 1},
    {"id": "general-25", "question": "Which restart follows when a defender last touches the ball over their own goal line without a goal?", "options": ["Goal kick","Free kick","Corner kick","Drop ball"], "answer": 2},
    {"id": "general-26", "question": "What is the term for scoring two goals in one match?", "options": ["Brace","Hat-trick","Clean sheet","Assist"], "answer": 0},
    {"id": "general-27", "question": "What is a clean sheet?", "options": ["A match without conceding a goal","A match with no fouls","A match without substitutions","A match without cards"], "answer": 0},
    {"id": "general-28", "question": "What is the primary job of a centre-back?", "options": ["Defend central areas","Take every corner","Stay beyond the forwards","Officiate substitutions"], "answer": 0},
    {"id": "general-29", "question": "Which player typically operates on the side of the attack?", "options": ["Winger","Goalkeeper","Centre-back","Referee"], "answer": 0},
    {"id": "general-30", "question": "What does a defensive midfielder usually help protect?", "options": ["The area in front of the defence","The corner flag","The technical area","The opposition bench"], "answer": 0},
    {"id": "general-31", "question": "What is an assist in football statistics?", "options": ["A contribution directly setting up a goal","A saved penalty","A substitution","A yellow card"], "answer": 0},
    {"id": "general-32", "question": "What is a derby?", "options": ["A rivalry match often involving nearby clubs","A match played only at night","A friendly without referees","A match that must end in penalties"], "answer": 0},
    {"id": "general-33", "question": "What does aggregate score mean in a two-leg tie?", "options": ["Total goals across both matches","Goals scored in extra time only","Only the home team's goals","The number of yellow cards"], "answer": 0},
    {"id": "general-34", "question": "What is extra time in a knockout match?", "options": ["An additional period after a tied match when required","Added time at the end of a half","A longer halftime","A replay on another day"], "answer": 0},
    {"id": "general-35", "question": "What happens in a penalty shootout?", "options": ["Teams alternate penalty kicks to decide a tie","Every player takes a corner","Both teams restart at midfield","The referee awards a draw"], "answer": 0},
    {"id": "general-36", "question": "What does a captain commonly wear to identify their role?", "options": ["Armband","Different boots","Goalkeeper gloves","A second shirt"], "answer": 0},
    {"id": "general-37", "question": "What is a through ball?", "options": ["A pass played into space behind defenders","A ball thrown from the touchline","A corner kick","A goal kick"], "answer": 0},
    {"id": "general-38", "question": "What is a counterattack?", "options": ["A quick attack after winning possession","A substitution at halftime","A defensive wall","A throw-in routine"], "answer": 0},
    {"id": "general-39", "question": "What is possession percentage intended to measure?", "options": ["Share of time a team controls the ball","Share of shots on target","Share of successful tackles","Share of corners won"], "answer": 0},
    {"id": "general-40", "question": "What is a set piece?", "options": ["A restart such as a free kick or corner","A team photograph","A pre-match warmup","A formation change only"], "answer": 0},
    {"id": "general-41", "question": "What is the usual role of a full-back?", "options": ["Defend a wide area and support attacks","Stay in the centre circle","Only take penalties","Manage substitutions"], "answer": 0},
    {"id": "general-42", "question": "What is a false nine?", "options": ["A central attacker who often drops deeper","A goalkeeper wearing number nine","A defender who takes corners","A player serving a suspension"], "answer": 0},
    {"id": "general-43", "question": "What does pressing mean?", "options": ["Applying pressure to opponents in possession","Passing only backwards","Waiting in the penalty area","Taking a free kick"], "answer": 0},
    {"id": "general-44", "question": "What is a high defensive line?", "options": ["Defenders positioned farther up the pitch","A taller goal frame","An extra sideline","A formation without midfielders"], "answer": 0},
    {"id": "general-45", "question": "What is a one-two pass?", "options": ["A quick pass and return between teammates","A throw-in followed by a corner","Two shots in one move","A pass between goalkeepers"], "answer": 0},
    {"id": "general-46", "question": "What is a volley?", "options": ["Striking the ball before it touches the ground","A pass from the centre circle","A sliding tackle","A headed clearance"], "answer": 0},
    {"id": "general-47", "question": "What is a header?", "options": ["Playing the ball with the head","A pass with the heel","A referee signal","A goal from a penalty"], "answer": 0},
    {"id": "general-48", "question": "What is a substitution?", "options": ["Replacing one player with another","Changing the match ball","Moving the goalposts","Switching referees"], "answer": 0},
    {"id": "general-49", "question": "What is a formation such as 4-3-3 describing?", "options": ["Outfield player arrangement by lines","The final score","The number of substitutes","The referee crew"], "answer": 0},
    {"id": "general-50", "question": "What does a 0-0 scoreline mean?", "options": ["Neither team has scored","The match was cancelled","Both teams lost points","The match must be replayed"], "answer": 0},
    {"id": "general-51", "question": "What is the halfway line used for?", "options": ["Dividing the pitch into two halves","Marking the penalty spot","Showing the goalkeeper area","Setting the corner arc"], "answer": 0},
    {"id": "general-52", "question": "What is a direct free kick?", "options": ["A free kick from which a goal can be scored directly","A kick taken only by a defender","A kick that must be passed twice","A kick taken from midfield only"], "answer": 0},
    {"id": "general-53", "question": "What is an indirect free kick?", "options": ["A free kick requiring another player's touch before a goal counts","A penalty kick","A corner kick","A throw-in"], "answer": 0},
    {"id": "general-54", "question": "What is the technical area?", "options": ["The designated coaching area beside the pitch","The six-yard box","The centre circle","The penalty arc"], "answer": 0},
    {"id": "general-55", "question": "What is the purpose of shin guards?", "options": ["Protect the lower legs","Improve ball speed","Mark team captains","Replace football boots"], "answer": 0},
    {"id": "general-56", "question": "What does a goalkeeper save?", "options": ["An attempt on goal","A corner flag","A substitution","A yellow card"], "answer": 0},
    {"id": "general-57", "question": "What is a tackle in football?", "options": ["An attempt to win the ball from an opponent","A pass across the pitch","A shot on goal","A goal celebration"], "answer": 0},
    {"id": "general-58", "question": "What is a cross?", "options": ["A ball delivered from a wide area toward the middle","A back-pass to the goalkeeper","A penalty kick","A referee gesture"], "answer": 0},
    {"id": "general-59", "question": "What is a nutmeg?", "options": ["Playing the ball through an opponent's legs","Scoring from a corner","A goalkeeper throw","A substitution"], "answer": 0},
    {"id": "general-60", "question": "What is the purpose of the centre circle at kick-off?", "options": ["Keep opponents the required distance from the ball","Mark the penalty area","Show where corners are taken","Define the technical area"], "answer": 0},
])

QUIZ_LEVELS = {
    1: {"theme": "Football Basics", "description": "General football rules and knowledge."},
    2: {"theme": "Know Your Club", "description": "Basic facts about your primary team."},
    3: {"theme": "Players & Club", "description": "Current players and deeper club knowledge."},
    4: {"theme": "Club Challenge", "description": "A harder mix of club and player knowledge."},
    5: {"theme": "Expert Mode", "description": "The hardest available team-focused questions."},
}


class QuizSubmission(BaseModel):
    answers: list[int]
    practice_round: int = 0


def quiz_id() -> str:
    return date.today().isoformat()


def quiz_level_from_completions(completions: int) -> int:
    return min(5, completions // 5 + 1)


def rewarded_quiz_completions(db: Session, user_id: int) -> int:
    return int(db.scalar(select(func.count(XPEvent.id)).where(
        XPEvent.user_id == user_id,
        XPEvent.source_type == "daily_quiz",
    )) or 0)


def quiz_context(db: Session, user) -> dict:
    completions = rewarded_quiz_completions(db, user.id)
    level = quiz_level_from_completions(completions)
    team = user.primary_team
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


async def get_or_create_daily_snapshot(db: Session, user) -> tuple[list[dict], dict]:
    today = quiz_id()
    existing = db.scalar(select(DailyQuizSnapshot).where(
        DailyQuizSnapshot.user_id == user.id,
        DailyQuizSnapshot.quiz_date == today,
    ))
    context = quiz_context(db, user)
    if existing:
        questions = json.loads(existing.questions_json)
        snapshot_team = None
        if existing.team_provider_id and existing.team_name:
            snapshot_team = {"id": existing.team_provider_id, "name": existing.team_name}
        snapshot_context = {
            **context,
            "level": existing.level,
            "theme": existing.theme,
            "team": snapshot_team,
        }
        return questions, snapshot_context

    rng = random.Random(f"{today}:{user.id}:{context['level']}:daily")
    # Prefer questions not seen in previous daily quizzes at the current level.
    previous = db.scalars(select(DailyQuizSnapshot).where(
        DailyQuizSnapshot.user_id == user.id,
        DailyQuizSnapshot.level == context["level"],
        DailyQuizSnapshot.quiz_date < today,
    )).all()
    seen_ids = set()
    for snapshot in previous:
        try:
            seen_ids.update(q["id"] for q in json.loads(snapshot.questions_json))
        except (ValueError, KeyError, TypeError):
            continue
    fresh = [q for q in GENERAL_QUESTIONS if q["id"] not in seen_ids]
    selected = rng.sample(fresh, min(5, len(fresh)))
    if len(selected) < 5:
        remaining = [q for q in GENERAL_QUESTIONS if q["id"] not in {item["id"] for item in selected}]
        selected.extend(rng.sample(remaining, 5 - len(selected)))
    questions = selected
    if context["level"] >= 2 and context["team"]:
        grounded = await build_team_questions(
            context["team"]["id"],
            context["team"]["name"],
            context["level"],
            today,
        )
        if grounded:
            # Favor this level's club questions; avoid previously served IDs.
            fresh_team = [q for q in grounded if q["id"] not in seen_ids]
            rng.shuffle(fresh_team)
            chosen_team = fresh_team[:5]
            general_needed = 5 - len(chosen_team)
            general_fallback = [q for q in questions if q["id"] not in {item["id"] for item in chosen_team}]
            questions = chosen_team + general_fallback[:general_needed]
            # Only reuse club questions when the fresh general pool cannot fill the quiz.
            if len(questions) < 5:
                repeats = [q for q in grounded if q["id"] not in {item["id"] for item in questions}]
                rng.shuffle(repeats)
                questions.extend(repeats[:5 - len(questions)])
            rng.shuffle(questions)

    team = context["team"]
    db.add(DailyQuizSnapshot(
        user_id=user.id,
        quiz_date=today,
        level=context["level"],
        theme=context["theme"],
        team_provider_id=team["id"] if team else None,
        team_name=team["name"] if team else None,
        questions_json=json.dumps(questions),
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(DailyQuizSnapshot).where(
            DailyQuizSnapshot.user_id == user.id,
            DailyQuizSnapshot.quiz_date == today,
        ))
        if existing:
            return json.loads(existing.questions_json), context
        raise
    return questions, context



async def build_practice_questions(db: Session, user, practice_round: int = 0) -> tuple[list[dict], dict]:
    context = quiz_context(db, user)
    daily_questions, _ = await get_or_create_daily_snapshot(db, user)
    daily_ids = {question["id"] for question in daily_questions}
    pool = list(GENERAL_QUESTIONS)
    if context["level"] >= 2 and context["team"]:
        grounded = await build_team_questions(
            context["team"]["id"],
            context["team"]["name"],
            context["level"],
            quiz_id() + ":practice",
        )
        pool.extend(grounded)
    previous = db.scalars(select(DailyQuizSnapshot).where(
        DailyQuizSnapshot.user_id == user.id,
        DailyQuizSnapshot.level == context["level"],
    )).all()
    seen_ids = set(daily_ids)
    for snapshot in previous:
        try:
            seen_ids.update(q["id"] for q in json.loads(snapshot.questions_json))
        except (ValueError, KeyError, TypeError):
            continue
    rng = random.Random(f"{quiz_id()}:{user.id}:{context['level']}:practice:{practice_round}")
    unseen = [question for question in pool if question["id"] not in seen_ids]
    chosen = rng.sample(unseen, min(5, len(unseen)))
    if len(chosen) < 5:
        fallback = [question for question in pool if question["id"] not in {q["id"] for q in chosen} and question["id"] not in daily_ids]
        chosen.extend(rng.sample(fallback, min(5 - len(chosen), len(fallback))))
    return chosen, context


@router.get("/practice")
async def practice_quiz(round: int = 0, request: Request, db: Session = Depends(get_db)) -> dict:
    user = require_user(request, db)
    safe_round = max(0, min(round, 1000))
    questions, context = await build_practice_questions(db, user, safe_round)
    return {
        "quiz_id": f"{quiz_id()}-practice",
        "title": f"{context['theme']} Practice",
        "questions": [{"id": q["id"], "question": q["question"], "options": q["options"]} for q in questions],
        "completed": False,
        "xp_available": 0,
        "practice": True,
        "quiz_level": context["level"],
        "unlocked_level": context["unlocked_level"],
        "theme": context["theme"],
        "description": "Practice with a different set of questions. Practice does not award XP or change your streak.",
        "team": context["team"],
        "days_to_next_level": context["days_to_next_level"],
    }


@router.post("/practice/submit")
async def submit_practice_quiz(submission: QuizSubmission, request: Request, db: Session = Depends(get_db)) -> dict:
    user = require_user(request, db)
    questions, context = await build_practice_questions(db, user, max(0, min(submission.practice_round, 1000)))
    if len(submission.answers) != len(questions):
        raise HTTPException(status_code=400, detail="Answer every question before submitting.")
    if any(answer < 0 or answer >= len(questions[index]["options"]) for index, answer in enumerate(submission.answers)):
        raise HTTPException(status_code=400, detail="One or more quiz answers are invalid.")
    correct = sum(answer == question["answer"] for answer, question in zip(submission.answers, questions))
    return {
        "quiz_id": f"{quiz_id()}-practice",
        "correct": correct,
        "total": len(questions),
        "score_percent": round((correct / len(questions)) * 100) if questions else 0,
        "xp_awarded": 0,
        "already_rewarded": True,
        "practice": True,
        "correct_answers": [question["answer"] for question in questions],
        "quiz": context,
        "progress": progress_summary(db, user.id),
    }

@router.get("/daily")
async def daily_quiz(request: Request, db: Session = Depends(get_db)) -> dict:
    user = require_user(request, db)
    event = db.scalar(select(XPEvent).where(
        XPEvent.user_id == user.id,
        XPEvent.source_type == "daily_quiz",
        XPEvent.source_id == quiz_id(),
    ))
    questions, context = await get_or_create_daily_snapshot(db, user)
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
async def submit_daily_quiz(submission: QuizSubmission, request: Request, db: Session = Depends(get_db)) -> dict:
    user = require_user(request, db)
    questions, context = await get_or_create_daily_snapshot(db, user)
    if len(submission.answers) != len(questions):
        raise HTTPException(status_code=400, detail="Answer every question before submitting.")
    if any(answer < 0 or answer >= len(questions[index]["options"]) for index, answer in enumerate(submission.answers)):
        raise HTTPException(status_code=400, detail="One or more quiz answers are invalid.")

    correct = sum(answer == question["answer"] for answer, question in zip(submission.answers, questions))
    score_percent = round((correct / len(questions)) * 100)
    source_id = quiz_id()
    existing = db.scalar(select(XPEvent).where(
        XPEvent.user_id == user.id,
        XPEvent.source_type == "daily_quiz",
        XPEvent.source_id == source_id,
    ))
    xp_awarded = 0
    analysis_token_awarded = False

    if not existing:
        xp_awarded = 50 + correct * 10
        db.add(XPEvent(user_id=user.id, amount=xp_awarded, source_type="daily_quiz", source_id=source_id))
        analysis_token_awarded = grant_quiz_token(db, user.id, source_id)
        record_activity_day(db, user.id)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            xp_awarded = 0
            analysis_token_awarded = False

    updated_context = quiz_context(db, user)
    return {
        "quiz_id": source_id,
        "correct": correct,
        "total": len(questions),
        "score_percent": score_percent,
        "xp_awarded": xp_awarded,
        "analysis_token_awarded": analysis_token_awarded,
        "already_rewarded": existing is not None or xp_awarded == 0,
        "correct_answers": [question["answer"] for question in questions],
        "quiz": {**context, "unlocked_level": updated_context["unlocked_level"], "days_to_next_level": updated_context["days_to_next_level"]},
        "progress": progress_summary(db, user.id),
    }
