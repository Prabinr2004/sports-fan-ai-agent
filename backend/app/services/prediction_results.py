from datetime import datetime, timedelta, timezone


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def actual_outcome(match: dict) -> str | None:
    if match.get("status") != "FINISHED":
        return None
    score = match.get("score") or {}
    home, away = score.get("home"), score.get("away")
    if home is None or away is None:
        return None
    if home > away:
        return "HOME"
    if away > home:
        return "AWAY"
    return "DRAW"


def result_check_due(result_status: str, kickoff_utc: str | None, result_checked_at: datetime | None, now: datetime, cooldown_minutes: int = 30) -> bool:
    kickoff = parse_utc(kickoff_utc)
    if result_status != "PENDING" or kickoff is None or kickoff > now:
        return False
    if result_checked_at is None:
        return True
    checked = result_checked_at
    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=timezone.utc)
    return checked <= now - timedelta(minutes=cooldown_minutes)
