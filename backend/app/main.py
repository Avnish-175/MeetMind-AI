from typing import Any, Dict

from fastapi import Depends, FastAPI, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.routes.auth import router as auth_router
from app.core.config import settings
from app.database.dependencies import get_db

app = FastAPI(
    title=settings.APP_NAME,
    description="Local-first Agentic Multimodal Meeting Intelligence and Productivity Assistant",
    version=settings.APP_VERSION,
)

app.include_router(auth_router)


@app.get("/", tags=["Status"])
def root() -> Dict[str, Any]:
    """Root endpoint returning basic application status."""
    return {
        "title": app.title,
        "description": app.description,
        "version": app.version,
        "status": "online",
    }


@app.get("/health", tags=["Health"])
def health_check() -> Dict[str, str]:
    """Health check endpoint returning application status."""
    return {
        "status": "healthy",
        "service": "MeetMind AI Backend",
        "version": app.version,
    }


@app.get("/health/database", tags=["Health"])
def database_health_check(db: Session = Depends(get_db)) -> JSONResponse:
    """Verify PostgreSQL connectivity with a lightweight query."""
    try:
        db.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "healthy", "database": "connected"},
        )
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "unavailable"},
        )
