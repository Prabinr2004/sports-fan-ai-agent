import random

import httpx
from fastapi import HTTPException

from app.services.football import get_football_provider


def shuffle_options(correct: str, distractors: list[str], seed: str) -> tuple[list[str], int]:
    unique_distractors = []
    for item in distractors:
        if item and item != correct and item not in unique_distractors:
            unique_distractors.append(item)
    options = [correct, *unique_distractors[:3]]
    if len(options) < 4:
        return [], -1
    rng = random.Random(seed)
    rng.shuffle(options)
    return options, options.index(correct)


async def build_team_questions(provider_team_id: str, team_name: str, level: int, day: str) -> list[dict]:
    provider = get_football_provider()
    try:
        team = await provider.get_team(provider_team_id)
        squad = await provider.get_squad(provider_team_id)
    except (httpx.HTTPError, HTTPException):
        return []

    questions: list[dict] = []

    if level >= 2:
        facts = [
            (
                "country",
                f"Which country is {team_name} from?",
                team.get("country"),
                ["England", "Spain", "Germany", "Italy", "France", "Portugal", "Netherlands"],
            ),
            (
                "venue",
                f"Which stadium is associated with {team_name}?",
                team.get("venue"),
                ["Old Trafford", "Anfield", "San Siro", "Allianz Arena", "Emirates Stadium", "Signal Iduna Park"],
            ),
        ]
        for key, question, correct, distractors in facts:
            if not correct:
                continue
            options, answer = shuffle_options(str(correct), distractors, f"{day}:{provider_team_id}:{key}")
            if options:
                questions.append({"id": f"club-{key}", "question": question, "options": options, "answer": answer})

    if level >= 3 and squad:
        positioned = [player for player in squad if player.get("name") and player.get("position")]
        for index, player in enumerate(positioned):
            distractors = list(dict.fromkeys(
                other.get("position")
                for other in positioned
                if other.get("position") and other.get("position") != player.get("position")
            ))
            options, answer = shuffle_options(
                str(player["position"]),
                distractors,
                f"{day}:{provider_team_id}:position:{index}",
            )
            if options:
                questions.append({
                    "id": f"player-position-{index}",
                    "question": f"What position is {player['name']} listed as for {team_name}?",
                    "options": options,
                    "answer": answer,
                })
            if len(questions) >= 5:
                break

    return questions
