from uuid import uuid4

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.progress import XPEvent
from app.models.user import User
from app.services.auth_security import hash_password
from app.services.demo_migration import migrate_demo_progress


def test_migration_preview_and_apply():
    with SessionLocal() as db:
        demo = db.scalar(select(User).where(User.email == "local@fansphere.dev"))
        if demo is None:
            demo = User(email="local@fansphere.dev", display_name="Demo", password_hash="local-development")
            db.add(demo)
            db.commit()
            db.refresh(demo)
        email = f"migration-{uuid4().hex}@example.com"
        target = User(email=email, display_name="New Fan", password_hash=hash_password("test-password-2026"))
        db.add(target)
        db.commit()
        db.refresh(target)
        event = XPEvent(user_id=demo.id, amount=7, source_type="migration_test", source_id=uuid4().hex)
        db.add(event)
        db.commit()
        event_id = event.id
        try:
            preview = migrate_demo_progress(db, email)
            assert not preview["applied"]
            assert db.get(XPEvent, event_id).user_id == demo.id
            result = migrate_demo_progress(db, email, apply=True)
            assert result["applied"]
            assert db.get(XPEvent, event_id).user_id == target.id
        finally:
            db.delete(db.get(XPEvent, event_id))
            db.delete(target)
            db.commit()


def test_migration_requires_registered_target():
    with SessionLocal() as db:
        try:
            migrate_demo_progress(db, "nonexistent@example.com", apply=True)
        except ValueError:
            pass
        else:
            raise AssertionError("Migration must reject missing target accounts")
