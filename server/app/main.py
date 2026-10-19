from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.api.routes.auth import router as auth_router
from app.api.routes.brd import router as brd_router
from app.api.routes.standard_document import (
    router as standard_document_router,
)
from app.api.routes.workspace import router as workspace_router
from app.core.audit import AuditMiddleware
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.session import SessionLocal
from app.integrations.drive.router import (
    router as drive_router,
)
from app.integrations.gmail.router import (
    router as gmail_router,
)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=settings.environment == "production",
)
app.add_middleware(AuditMiddleware)


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
    if settings.environment == "production" and not settings.expose_db_health:
        return Response(status_code=404)

    with SessionLocal() as db:
        db.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected",
    }


app.include_router(auth_router)
app.include_router(workspace_router)
app.include_router(standard_document_router)
app.include_router(brd_router)
app.include_router(gmail_router)
app.include_router(drive_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True,
    max_age=600,
)
