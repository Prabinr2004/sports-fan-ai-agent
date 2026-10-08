"""Credit 10 one-time test gems to a specified user in a LOCAL SQLite database only.

Run from backend: python scripts/grant_local_test_gems.py
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.database.session import SessionLocal, engine
from app.models.user import User
from app.models.gems import GemEvent
from app.services.gems import gem_balance

SOURCE_ID = "local-preview-10-gems-v1"

def main():
    if engine.dialect.name != "sqlite":
        raise SystemExit("Refusing to credit gems: this helper only supports local SQLite.")
    email = input("FanSphere login email: ").strip().lower()
    if not email:
        raise SystemExit("No email provided.")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            raise SystemExit("No account found for that email in this local database.")
        existing = db.scalar(select(GemEvent).where(
            GemEvent.user_id == user.id,
            GemEvent.source_type == "local_test_credit",
            GemEvent.source_id == SOURCE_ID,
        ))
        if existing is not None:
            print(f"Test credit already applied. Current balance: {gem_balance(db, user.id)} gems.")
            return
        confirm = input(f"Add 10 TEST gems to {email}? Type YES: ").strip()
        if confirm != "YES":
            raise SystemExit("Cancelled; no gems added.")
        db.add(GemEvent(user_id=user.id, amount=10, source_type="local_test_credit", source_id=SOURCE_ID))
        db.commit()
        print(f"Added 10 test gems. Current balance: {gem_balance(db, user.id)} gems.")

if __name__ == "__main__":
    main()
