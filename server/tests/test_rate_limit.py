"""Rate limits must follow the verified user, not a rotatable bearer token.

M-1: the key function keyed on sha256(token). Supabase access tokens rotate
on every refresh, so refreshing the session reset every bucket (defeating
the 5/hour BRD-generate cap and friends). Now get_current_user stashes the
verified JWT sub on request.state.user_id (post signature/audience/issuer
checks) and rate_limit_key keys on "user:<sub>", falling back to remote
address for headerless requests (e.g. Google OAuth callbacks). An
unverified sub is never trusted — a forged token cannot aim a bucket at
another user.
"""

from types import SimpleNamespace
from uuid import UUID, uuid4

import jwt
import pytest
from app.auth.dependencies import CurrentUser, get_current_user
from app.core.rate_limit import limiter, rate_limit_key
from app.main import rate_limit_exceeded_handler
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware


def make_request(
    headers: list | None = None,
    client: tuple = ("203.0.113.9", 40000),
    state: dict | None = None,
) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers or [],
        "client": client,
    }

    if state is not None:
        scope["state"] = state

    return Request(scope)


def test_key_prefers_verified_user_id_over_token():
    request = make_request(
        headers=[(b"authorization", b"Bearer some-rotating-token")],
        state={"user_id": "user-123"},
    )

    assert rate_limit_key(request) == "user:user-123"


def test_key_falls_back_to_remote_address_without_user():
    request = make_request(client=("198.51.100.7", 1234))

    assert rate_limit_key(request) == "198.51.100.7"


@pytest.fixture(scope="module")
def limited_client() -> TestClient:
    assert limiter.enabled, "tests require rate_limit_enabled=True"

    testapp = FastAPI()
    testapp.state.limiter = limiter
    testapp.add_middleware(SlowAPIMiddleware)
    testapp.add_exception_handler(
        RateLimitExceeded,
        rate_limit_exceeded_handler,
    )

    def fake_verified_user(request: Request) -> None:
        # Mirrors get_current_user's contract: verify first, then stash the
        # subject on request.state for the key function. Tokens here look
        # like "aaaa-<user-uuid>"; the prefix simulates token rotation.
        credentials = request.headers.get("authorization")

        if credentials is None:
            raise HTTPException(status_code=401)

        _, _, token = credentials.partition(" ")
        request.state.user_id = token.split("-", 1)[1]

    @testapp.get("/limited")
    @limiter.limit("2/minute")
    async def limited(
        request: Request,
        user=Depends(fake_verified_user),
    ) -> dict:
        return {"ok": True}

    return TestClient(testapp)


def test_rotated_token_same_user_shares_bucket(limited_client: TestClient):
    user_id = uuid4()
    first_token = {"Authorization": f"Bearer aaaa-{user_id}"}
    rotated_token = {"Authorization": f"Bearer bbbb-{user_id}"}

    assert (
        limited_client.get("/limited", headers=first_token).status_code
        == 200
    )
    assert (
        limited_client.get("/limited", headers=first_token).status_code
        == 200
    )

    # M-1 regression: a rotated token for the same user must NOT reset the
    # bucket.
    exceeded = limited_client.get("/limited", headers=rotated_token)
    assert exceeded.status_code == 429
    assert exceeded.headers.get("Retry-After") == "60"


def test_rate_limit_buckets_are_per_user(limited_client: TestClient):
    user_a = uuid4()
    user_b = uuid4()
    headers_a = {"Authorization": f"Bearer aaaa-{user_a}"}
    headers_b = {"Authorization": f"Bearer bbbb-{user_b}"}

    for _ in range(2):
        assert (
            limited_client.get("/limited", headers=headers_a).status_code
            == 200
        )

    assert limited_client.get("/limited", headers=headers_a).status_code == 429

    # Exhausting user A's bucket leaves user B untouched.
    assert limited_client.get("/limited", headers=headers_b).status_code == 200


def test_get_current_user_stashes_verified_sub(monkeypatch):
    sub = str(uuid4())

    monkeypatch.setattr(
        "app.auth.dependencies.get_jwks_client",
        lambda: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(
                key="test-key",
            ),
        ),
    )
    monkeypatch.setattr(
        jwt,
        "decode",
        lambda *_args, **_kwargs: {"sub": sub, "email": "user@example.com"},
    )

    request = make_request()
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="fake-token",
    )

    user = get_current_user(request=request, credentials=credentials)

    assert isinstance(user, CurrentUser)
    assert user.id == UUID(sub)
    assert request.state.user_id == sub
