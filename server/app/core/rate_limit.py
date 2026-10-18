from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings


def rate_limit_key(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)

    if user_id is not None:
        return f"user:{user_id}"

    return get_remote_address(request)


limiter = Limiter(
    key_func=rate_limit_key,
    enabled=settings.rate_limit_enabled,
)
