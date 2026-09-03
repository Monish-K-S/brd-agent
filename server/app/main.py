from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal

from app.api.routes.auth import router as auth_router
from app.api.routes.workspace import router as workspace_router
from app.api.routes.standard_document import (
    router as standard_document_router,
)
from app.api.routes.document_extraction import (
    router as document_extraction_router,
)


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


app.include_router(auth_router)
app.include_router(workspace_router)
app.include_router(standard_document_router)
app.include_router(document_extraction_router)
