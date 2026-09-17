from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.api.routes.auth import router as auth_router
from app.api.routes.brd import router as brd_router
from app.api.routes.document_extraction import (
    router as document_extraction_router,
)
from app.api.routes.project_knowledge import (
    router as project_knowledge_router,
)
from app.api.routes.standard_document import (
    router as standard_document_router,
)
from app.api.routes.workspace import router as workspace_router
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import SessionLocal
from app.integrations.gmail.router import (
    router as gmail_router,
)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


def _retry_after_seconds(exc: RateLimitExceeded) -> int:
    granularity = str(getattr(exc.limit, "limit", "")).lower()

    if "second" in granularity:
        return 1

    if "minute" in granularity:
        return 60

    if "day" in granularity:
        return 86400

    return 3600


@app.exception_handler(RateLimitExceeded)
def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    retry_seconds = _retry_after_seconds(exc)

    return JSONResponse(
        status_code=429,
        content={
            "detail": (
                "Rate limit exceeded. "
                f"Try again in {retry_seconds}s."
            ),
        },
        headers={"Retry-After": str(retry_seconds)},
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
app.include_router(project_knowledge_router)
app.include_router(brd_router)
app.include_router(gmail_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
