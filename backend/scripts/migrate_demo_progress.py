"""Preview or transfer legacy local progress to a registered FanSphere account.

From backend/: python scripts/migrate_demo_progress.py --email you@example.com
Apply only after reviewing the preview and backing up the SQLite database.
"""
import argparse
import json
import sys
from pathlib import Path

# Support invocation as: python scripts/migrate_demo_progress.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.session import SessionLocal
from app.models import analysis, prediction, progress, quiz, team, user  # noqa: F401
from app.services.demo_migration import migrate_demo_progress


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Already registered FanSphere email")
    parser.add_argument("--source-user-id", type=int, help="Explicit source account ID (defaults to legacy demo)")
    parser.add_argument("--apply", action="store_true", help="Actually transfer records")
    args = parser.parse_args()
    if args.apply:
        confirmation = input(f"Type TRANSFER to move records from source ID {args.source_user_id or 'legacy demo'} into {args.email}: ")
        if confirmation != "TRANSFER":
            raise SystemExit("Cancelled without changes.")
    with SessionLocal() as db:
        result = migrate_demo_progress(db, args.email, apply=args.apply, source_user_id=args.source_user_id)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
