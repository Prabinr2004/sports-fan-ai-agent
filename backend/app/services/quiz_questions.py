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
    team, squad = {}, []
    try:
        team = await provider.get_team(provider_team_id)
        squad = await provider.get_squad(provider_team_id)
    except (httpx.HTTPError, HTTPException):
        # Historical questions remain available during provider outages.
        pass

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

    # Verified historical questions for Real Madrid; other clubs keep provider-grounded questions.
    if "real madrid" in team_name.casefold():
        history = [
            (3, "rm-threepeat-years", "In which three years did Real Madrid win three consecutive Champions League titles?", "2016, 2017, 2018", ["2014, 2015, 2016", "2015, 2016, 2017", "2017, 2018, 2019"]),
            (3, "rm-threepeat-coach", "Who coached Real Madrid to the 2016–2018 Champions League three-peat?", "Zinedine Zidane", ["Carlo Ancelotti", "José Mourinho", "Rafael Benítez"]),
            (3, "rm-record-scorer", "Who is Real Madrid's all-time leading goalscorer?", "Cristiano Ronaldo", ["Karim Benzema", "Raúl González", "Alfredo Di Stéfano"]),
            (4, "rm-decima-year", "In which year did Real Madrid win La Décima, their tenth European Cup?", "2014", ["2012", "2016", "2018"]),
            (4, "rm-decima-coach", "Who coached Real Madrid to La Décima in 2014?", "Carlo Ancelotti", ["Zinedine Zidane", "José Mourinho", "Rafael Benítez"]),
            (4, "rm-2018-final", "Which club did Real Madrid beat in the 2018 Champions League final?", "Liverpool", ["Juventus", "Atlético Madrid", "Bayern Munich"]),
            (4, "rm-2017-final", "Which club did Real Madrid beat in the 2017 Champions League final?", "Juventus", ["Liverpool", "Atlético Madrid", "Manchester City"]),
            (5, "rm-2018-final-bale", "Who scored twice for Real Madrid in the 2018 Champions League final?", "Gareth Bale", ["Karim Benzema", "Cristiano Ronaldo", "Isco"]),
            (5, "rm-2017-final-ronaldo", "Who scored twice for Real Madrid in the 2017 Champions League final?", "Cristiano Ronaldo", ["Gareth Bale", "Karim Benzema", "Sergio Ramos"]),
            (5, "rm-record-goals", "How many official goals did Cristiano Ronaldo score for Real Madrid?", "450", ["438", "312", "405"]),
            (5, "rm-2014-final-opponent", "Who did Real Madrid defeat in the 2014 Champions League final?", "Atlético Madrid", ["Juventus", "Liverpool", "Barcelona"]),
            (5, "rm-2018-final-city", "In which city was the 2018 Champions League final played?", "Kyiv", ["Cardiff", "Lisbon", "Milan"]),
        ]
        for minimum_level, question_id, question, correct, distractors in history:
            if level == minimum_level:
                add(question_id, question, correct, distractors)

    # Stable historical facts do not depend on the live squad feed.
    club = team_name.casefold().strip()
    historical = {
        "liverpool": [
            (3, "liv-2005-coach", "Who managed Liverpool when they won the 2005 Champions League?", "Rafael Benítez", ["Jürgen Klopp", "Gérard Houllier", "Roy Hodgson"]),
            (3, "liv-2005-final", "Which club did Liverpool defeat in the 2005 Champions League final?", "AC Milan", ["Juventus", "Real Madrid", "Barcelona"]),
            (3, "liv-record-scorer", "Who is Liverpool's all-time leading goalscorer?", "Ian Rush", ["Steven Gerrard", "Mohamed Salah", "Robbie Fowler"]),
            (4, "liv-2005-city", "In which city was Liverpool's 2005 Champions League comeback final played?", "Istanbul", ["Athens", "Rome", "Madrid"]),
            (4, "liv-2019-final", "Who did Liverpool beat in the 2019 Champions League final?", "Tottenham Hotspur", ["Chelsea", "Bayern Munich", "Ajax"]),
            (4, "liv-2019-coach", "Who managed Liverpool when they won the 2019 Champions League?", "Jürgen Klopp", ["Rafael Benítez", "Brendan Rodgers", "Kenny Dalglish"]),
            (5, "liv-2005-penalties", "Who was Liverpool's goalkeeper in the 2005 Champions League final shootout?", "Jerzy Dudek", ["Pepe Reina", "Alisson Becker", "Simon Mignolet"]),
            (5, "liv-2019-opening-goal", "Who scored Liverpool's opening goal in the 2019 Champions League final?", "Mohamed Salah", ["Sadio Mané", "Divock Origi", "Roberto Firmino"]),
        ],
        "manchester united": [
            (3, "mun-1999-manager", "Who managed Manchester United during their 1999 treble season?", "Alex Ferguson", ["Matt Busby", "José Mourinho", "Louis van Gaal"]),
            (3, "mun-1999-final", "Who did Manchester United beat in the 1999 Champions League final?", "Bayern Munich", ["Juventus", "Barcelona", "Real Madrid"]),
            (3, "mun-record-scorer", "Who is Manchester United's all-time leading goalscorer?", "Wayne Rooney", ["Bobby Charlton", "Cristiano Ronaldo", "Denis Law"]),
            (4, "mun-1999-winning-goal", "Who scored Manchester United's winning goal in the 1999 Champions League final?", "Ole Gunnar Solskjær", ["Teddy Sheringham", "David Beckham", "Ryan Giggs"]),
            (4, "mun-2008-final", "Which club did Manchester United defeat in the 2008 Champions League final?", "Chelsea", ["Arsenal", "Liverpool", "Barcelona"]),
            (4, "mun-2008-coach", "Who managed Manchester United when they won the 2008 Champions League?", "Alex Ferguson", ["David Moyes", "José Mourinho", "Ron Atkinson"]),
            (5, "mun-1999-equaliser", "Who scored Manchester United's equaliser in the 1999 Champions League final?", "Teddy Sheringham", ["Ole Gunnar Solskjær", "Paul Scholes", "Dwight Yorke"]),
            (5, "mun-2008-final-city", "In which city was the 2008 Champions League final played?", "Moscow", ["London", "Rome", "Munich"]),
        ],
        "barcelona": [
            (3, "bar-2009-coach", "Who coached Barcelona to the 2009 Champions League title?", "Pep Guardiola", ["Frank Rijkaard", "Luis Enrique", "Johan Cruyff"]),
            (3, "bar-2009-final", "Who did Barcelona defeat in the 2009 Champions League final?", "Manchester United", ["Chelsea", "Arsenal", "Bayern Munich"]),
            (3, "bar-record-scorer", "Who is Barcelona's all-time leading goalscorer?", "Lionel Messi", ["Luis Suárez", "César Rodríguez", "Samuel Eto'o"]),
            (4, "bar-2015-coach", "Who coached Barcelona to the 2015 Champions League title?", "Luis Enrique", ["Pep Guardiola", "Frank Rijkaard", "Xavi Hernández"]),
            (4, "bar-2015-final", "Who did Barcelona beat in the 2015 Champions League final?", "Juventus", ["Manchester United", "Bayern Munich", "Real Madrid"]),
            (4, "bar-2006-final", "Who did Barcelona beat in the 2006 Champions League final?", "Arsenal", ["Chelsea", "Liverpool", "AC Milan"]),
            (5, "bar-2009-second-goal", "Who scored Barcelona's second goal in the 2009 Champions League final?", "Lionel Messi", ["Samuel Eto'o", "Xavi", "Andrés Iniesta"]),
            (5, "bar-2015-final-city", "In which city was the 2015 Champions League final played?", "Berlin", ["Rome", "Lisbon", "Paris"]),
        ],
    }
    for club_key, items in historical.items():
        if club == club_key or club.startswith(club_key + " "):
            for required_level, question_id, question, correct, distractors in items:
                if level == required_level:
                    add(question_id, question, correct, distractors)
            break

    return questions
