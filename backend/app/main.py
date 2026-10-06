from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.leaderboard import router as leaderboard_router
from app.api.matches import router as matches_router
from app.api.ml_predictions import router as ml_predictions_router
from app.api.profile import router as profile_router
from app.api.quiz import router as quiz_router
from app.api.teams import router as teams_router
from app.core.config import settings
from app.database.session import Base, engine
from app.models import prediction as prediction_models  # noqa: F401
from app.models import progress as progress_models  # noqa: F401
from app.models import team as team_models  # noqa: F401
from app.models import user as user_models  # noqa: F401


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="2.0.0-dev", description="Personalized football fan platform with ML predictions and AI assistance.")
    app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    @app.on_event("startup")
    def create_local_tables() -> None:
        Base.metadata.create_all(bind=engine)

    app.include_router(health_router, prefix=settings.api_v1_prefix)
    app.include_router(teams_router, prefix=settings.api_v1_prefix)
    app.include_router(profile_router, prefix=settings.api_v1_prefix)
    app.include_router(quiz_router, prefix=settings.api_v1_prefix)
    app.include_router(matches_router, prefix=settings.api_v1_prefix)
    app.include_router(ml_predictions_router, prefix=settings.api_v1_prefix)
    app.include_router(leaderboard_router, prefix=settings.api_v1_prefix)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"name": settings.app_name, "version": "2.0.0-dev", "docs": "/docs", "health": f"{settings.api_v1_prefix}/health"}

    return app


app = create_app()
