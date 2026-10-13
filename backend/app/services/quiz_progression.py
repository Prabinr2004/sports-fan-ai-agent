"""Rules for the three-level rewarded quiz progression.

Each level has 12 rewarded rounds of five questions. Seven completed rounds
unlock the next level; players may still complete the remaining five rounds.
Unlocks are global across clubs, while each round belongs to its chosen level.
"""

MAX_LEVEL = 3
ROUNDS_PER_LEVEL = 12
ROUNDS_TO_UNLOCK = 7
QUESTIONS_PER_ROUND = 5


def unlocked_level(rounds_by_level: dict[int, int], legacy_unlocked_level: int = 1) -> int:
    """Keep any level already unlocked under the previous progression system."""
    level = max(1, min(MAX_LEVEL, legacy_unlocked_level))
    if rounds_by_level.get(1, 0) >= ROUNDS_TO_UNLOCK:
        level = max(level, 2)
    if rounds_by_level.get(2, 0) >= ROUNDS_TO_UNLOCK:
        level = max(level, 3)
    return level


def can_play_rewarded(level: int, rounds_by_level: dict[int, int], highest_unlocked: int) -> bool:
    return 1 <= level <= min(MAX_LEVEL, highest_unlocked) and rounds_by_level.get(level, 0) < ROUNDS_PER_LEVEL


def level_progress(level: int, rounds_by_level: dict[int, int], highest_unlocked: int) -> dict:
    if not 1 <= level <= MAX_LEVEL:
        raise ValueError("Unsupported quiz level")
    completed = max(0, rounds_by_level.get(level, 0))
    return {
        "level": level,
        "rounds_completed": min(completed, ROUNDS_PER_LEVEL),
        "rounds_remaining": max(0, ROUNDS_PER_LEVEL - completed),
        "unlocked": level <= highest_unlocked,
        "next_level_unlocked": level < MAX_LEVEL and highest_unlocked > level,
        "rounds_to_unlock_next": max(0, ROUNDS_TO_UNLOCK - completed) if level < MAX_LEVEL else 0,
        "rewarded_available": can_play_rewarded(level, rounds_by_level, highest_unlocked),
    }
