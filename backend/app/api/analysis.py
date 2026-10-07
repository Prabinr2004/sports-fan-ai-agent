from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.profile import _get_or_create_local_user
from app.database.session import get_db
from app.services.analysis_access import analysis_access_summary, unlock_analysis

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/access")
def get_analysis_access(db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    return analysis_access_summary(db, user.id)


@router.post("/{match_id}/unlock")
def unlock_match_analysis(match_id: str, db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    return unlock_analysis(db, user.id, match_id)
