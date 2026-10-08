"""Isolate pytest data from the local FanSphere development database.

Pytest imports this conftest before collecting test modules, which import the
application and initialize its SQLAlchemy engine. Never import app above this.
"""
import os
import tempfile
from pathlib import Path

# A fresh database for each pytest invocation, outside the project directory.
_test_dir = Path(tempfile.mkdtemp(prefix="fansphere-pytest-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_test_dir / 'test.db'}"

def pytest_sessionstart(session):
    from app.database.session import engine
    from sqlalchemy.engine import make_url

    actual = make_url(str(engine.url))
    expected = (_test_dir / "test.db").resolve()
    if actual.get_backend_name() != "sqlite" or Path(actual.database or "").resolve() != expected:
        raise RuntimeError("Refusing to run tests: database is not the isolated pytest database.")

def pytest_sessionfinish(session, exitstatus):
    # Keep the test DB for debugging; it is never the user's app database.
    pass
