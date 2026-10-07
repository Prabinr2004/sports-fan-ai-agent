import httpx

from app.core.config import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class AIAnalysisUnavailable(Exception):
    pass


async def explain_match(*, home_team: str, away_team: str, competition: str | None, model_outlook: dict | None, comparison: dict | None) -> str:
    if not settings.openrouter_api_key:
        raise AIAnalysisUnavailable("Rich FanSphere analysis is not configured.")

    context = {
        "competition": competition or "Football",
        "home_team": home_team,
        "away_team": away_team,
        "model_outlook": model_outlook,
        "team_comparison": comparison,
    }
    prompt = (
        "You are FanSphere's football match analyst. Explain the supplied structured pre-match data only. "
        "Do not invent injuries, lineups, news, statistics, or facts that are absent. "
        "Do not mention betting, odds, wagering, or gambling. "
        "Write 3 short sections: Model read, Key factors, What could change the match. "
        "Be concise and make uncertainty clear.\n\n"
        f"DATA: {context}"
    )
    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 350,
    }
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            if not text:
                raise AIAnalysisUnavailable("Rich FanSphere analysis returned an empty response.")
            return text
    except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
        raise AIAnalysisUnavailable("Rich FanSphere analysis is temporarily unavailable.") from exc
