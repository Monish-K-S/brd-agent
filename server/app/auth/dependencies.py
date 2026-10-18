from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from pydantic import BaseModel

from app.core.audit import audit
from app.core.config import settings


security = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    id: UUID
    email: str | None = None


@lru_cache
def get_jwks_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(
        f"{settings.supabase_url}/auth/v1/.well-known/jwks.json",
        timeout=5,
    )


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        security,
    ),
) -> CurrentUser:
    if credentials is None:
        audit(event="auth.failure", outcome="missing_credentials")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    token = credentials.credentials

    try:
        signing_key = get_jwks_client().get_signing_key_from_jwt(
            token,
        )
    except jwt.PyJWKClientConnectionError:
        audit(event="auth.failure", outcome="jwks_unavailable")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )
    except (jwt.PyJWTError, ValueError):
        audit(event="auth.failure", outcome="invalid_token")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    try:
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            issuer=f"{settings.supabase_url}/auth/v1",
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )

        # Verified sub (signature/audience/issuer checked above) — exposed
        # for the rate-limit key function so limits follow the user, not a
        # rotatable bearer token.
        request.state.user_id = user_id

        return CurrentUser(
            id=UUID(user_id),
            email=payload.get("email"),
        )

    except (jwt.PyJWTError, ValueError):
        audit(event="auth.failure", outcome="invalid_token")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
