"""Non-repeating question selection for a 60-question quiz bank."""
import random


class QuizBankExhausted(ValueError):
    pass


def select_unseen_questions(questions: list[dict], seen_ids: set[str], *, count: int = 5, seed: str) -> list[dict]:
    ids = [item["id"] for item in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate question IDs")
    available = [item for item in questions if item["id"] not in seen_ids]
    if len(available) < count:
        raise QuizBankExhausted("Not enough unseen questions for a complete round")
    return random.Random(seed).sample(available, count)


def question_history_key(level: int, team_provider_id: str | None) -> str:
    if level == 1:
        return "level:1:global"
    if level not in (2, 3) or not team_provider_id:
        raise ValueError("A primary team is required for club questions")
    return f"level:{level}:team:{team_provider_id}"
