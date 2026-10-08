import random

import httpx
from fastapi import HTTPException

from app.services.football import get_football_provider


def shuffle_options(correct: str, distractors: list[str], seed: str) -> tuple[list[str], int]:
    unique_distractors = []
    for item in distractors:
        if item and item.casefold() != correct.casefold() and item.casefold() not in {value.casefold() for value in unique_distractors}:
            unique_distractors.append(item)
    options = [correct, *unique_distractors[:3]]
    if len(options) < 4:
        return [], -1
    rng = random.Random(seed)
    rng.shuffle(options)
    return options, options.index(correct)


def numeric_distractors(value: int, offsets: tuple[int, ...] = (-2, -1, 1, 2, 5, -5)) -> list[str]:
    return [str(value + offset) for offset in offsets if value + offset > 0]


async def build_team_questions(provider_team_id: str, team_name: str, level: int, day: str) -> list[dict]:
    provider = get_football_provider()
    try:
        team = await provider.get_team(provider_team_id)
        squad = await provider.get_squad(provider_team_id)
    except (httpx.HTTPError, HTTPException):
        return []

    questions: list[dict] = []

    def add(question_id: str, question: str, correct: object, distractors: list[str]) -> None:
        if correct is None or str(correct).strip() == "":
            return
        options, answer = shuffle_options(str(correct), distractors, f"{day}:{provider_team_id}:{question_id}")
        if options:
            questions.append({"id": question_id, "question": question, "options": options, "answer": answer})

    if level == 2:
        add(
            "club-country",
            f"Which country is {team_name} from?",
            team.get("country"),
            ["England", "Spain", "Germany", "Italy", "France", "Portugal", "Netherlands"],
        )
        add(
            "club-venue",
            f"Which stadium is associated with {team_name}?",
            team.get("venue"),
            ["Old Trafford", "Anfield", "San Siro", "Allianz Arena", "Emirates Stadium", "Signal Iduna Park"],
        )
        founded = team.get("founded")
        if isinstance(founded, int):
            add(
                "club-founded",
                f"In which year was {team_name} founded?",
                founded,
                numeric_distractors(founded, (-10, -5, 5, 10, -15, 15)),
            )
        add(
            "club-colors",
            f"Which club colors are listed for {team_name}?",
            team.get("club_colors"),
            ["Red / White", "Blue / White", "Black / White", "Red / Blue", "Green / White", "Yellow / Black"],
        )

    positioned = [player for player in squad if player.get("id") and player.get("name") and player.get("position")]

    if level == 3 and positioned:
        positions = list(dict.fromkeys(str(player["position"]) for player in positioned if player.get("position")))
        nationalities = list(dict.fromkeys(str(player["nationality"]) for player in positioned if player.get("nationality")))

        for player in positioned:
            player_id = str(player["id"])
            position = str(player["position"])
            add(
                f"player-position-{player_id}",
                f"What position is {player['name']} listed as for {team_name}?",
                position,
                [value for value in positions if value != position],
            )
            if player.get("nationality") and len(nationalities) >= 4:
                nationality = str(player["nationality"])
                add(
                    f"player-nationality-{player_id}",
                    f"Which nationality is listed for {player['name']} in the current {team_name} squad?",
                    nationality,
                    [value for value in nationalities if value != nationality],
                )

    if level == 4 and positioned:
        for player in positioned:
            same_position = [p for p in positioned if p.get("position") == player.get("position")]
            other_names = [str(p["name"]) for p in positioned if p.get("id") != player.get("id") and p.get("position") != player.get("position")]
            if len(same_position) == 1:
                add(
                    f"identify-position-{player['id']}",
                    f"Which current {team_name} player is listed as {player['position']}?",
                    player["name"],
                    other_names,
                )

    if level == 5:
        for player in positioned:
            dob = str(player.get("date_of_birth") or "")
            if len(dob) >= 4 and dob[:4].isdigit():
                year = int(dob[:4])
                add(
                    f"player-birth-year-{player['id']}",
                    f"In which year was {player['name']} born?",
                    year,
                    numeric_distractors(year),
                )

    return questions
