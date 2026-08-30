from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from pydantic import BaseModel

from app.core.config import settings


security = HTTPBearer()


class CurrentUser(BaseModel):
    id: UUID
    email: str | None = None


@lru_cache
def get_jwks_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(
        f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security,
    ),
) -> CurrentUser:
    token = credentials.credentials

    try:
        signing_key = get_jwks_client().get_signing_key_from_jwt(
            token,
        )

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

        return CurrentUser(
            id=UUID(user_id),
            email=payload.get("email"),
        )

    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
