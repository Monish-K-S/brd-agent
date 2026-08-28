from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "environment": settings.environment,
    }


@app.get("/health/database")
def database_health_check():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected",
    }
