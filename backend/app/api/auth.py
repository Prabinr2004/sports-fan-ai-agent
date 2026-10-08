"""Opt-in account endpoints. Existing demo routes are unchanged until migration."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth_session import AuthSession
from app.models.user import User
from app.services.auth_security import hash_password, new_session_token, token_digest, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE_NAME = "fansphere_session"
SESSION_DAYS = 14


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Registration(Credentials):
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=2, max_length=60)


def _current_user(request: Request, db: Session) -> User | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_digest(token)))
    if not session or session.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        return None
    return db.get(User, session.user_id)


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = _current_user(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to access your FanSphere account.")
    return user


def _set_session(response: Response, request: Request, db: Session, user: User) -> None:
    token = new_session_token()
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    db.add(AuthSession(user_id=user.id, token_hash=token_digest(token), expires_at=expires))
    db.commit()
    response.set_cookie(
        COOKIE_NAME, token, max_age=SESSION_DAYS * 86400,
        httponly=True, secure=request.url.scheme == "https",
        samesite="strict", path="/",
    )


def _public_user(user: User) -> dict:
    return {"id": user.id, "email": user.email, "display_name": user.display_name}


@router.post("/register", status_code=201)
def register(payload: Registration, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    email = str(payload.email).strip().lower()
    if email == "local@fansphere.dev":
        raise HTTPException(status_code=400, detail="This email is reserved for the existing demo account.")
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    name = payload.display_name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Display name must have at least two characters.")
    user = User(email=email, display_name=name, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    db.refresh(user)
    _set_session(response, request, db, user)
    return {"user": _public_user(user)}


@router.post("/login")
def login(payload: Credentials, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == str(payload.email).strip().lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    _set_session(response, request, db, user)
    return {"user": _public_user(user)}


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)) -> dict:
    user = _current_user(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return {"user": _public_user(user)}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_digest(token)))
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(COOKIE_NAME, path="/", samesite="strict")
    return {"signed_out": True}
