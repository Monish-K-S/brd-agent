import hashlib

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings


def rate_limit_key(request: Request) -> str:
    authorization = request.headers.get("authorization")

    if authorization:
        scheme, _, token = authorization.partition(" ")

        if scheme.lower() == "bearer" and token.strip():
            digest = hashlib.sha256(token.strip().encode()).hexdigest()

            return f"user:{digest}"

    return get_remote_address(request)


limiter = Limiter(
    key_func=rate_limit_key,
    enabled=settings.rate_limit_enabled,
)
