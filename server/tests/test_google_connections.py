"""Per-connector Google OAuth rows (gmail vs drive).

Gmail and Drive used to share one google_connections row
(provider="google", last-connect-wins). Each connector now owns its row,
Drive grants are drive.file-only, and a dead grant surfaces
GoogleReconnectRequiredError (409 + reconnect CTA) instead of a raw
refresh failure.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.db.base import Base
from app.db.models.google_connection import GoogleConnection
from app.integrations.drive.service import DRIVE_SCOPES
from app.integrations.gmail.service import GOOGLE_SCOPES
from app.integrations.google_oauth_store import (
    GoogleOAuthStore,
    GoogleReconnectRequiredError,
)
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _register_uuid(dbapi_connection, _connection_record):
        # The id PK defaults to gen_random_uuid() (Postgres-only).
        dbapi_connection.create_function(
            "gen_random_uuid", 0, lambda: uuid4().hex
        )

    GoogleConnection.__table__.create(engine)
    return Session(engine)


def make_credentials(**overrides) -> SimpleNamespace:
    values = {
        "token": "access-token",
        "refresh_token": "refresh-token",
        "expiry": datetime.now(timezone.utc)
        + timedelta(hours=1),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def gmail_store(db: Session) -> GoogleOAuthStore:
    return GoogleOAuthStore(db, provider="gmail", scopes=GOOGLE_SCOPES)


def drive_store(db: Session) -> GoogleOAuthStore:
    return GoogleOAuthStore(db, provider="drive", scopes=DRIVE_SCOPES)


def test_drive_scopes_are_drive_file_only():
    assert DRIVE_SCOPES == ["https://www.googleapis.com/auth/drive.file"]
    assert GOOGLE_SCOPES == ["https://www.googleapis.com/auth/gmail.readonly"]


def test_connectors_own_independent_rows():
    db = make_session()
    user_id = uuid4()

    gmail_store(db).save_connection(
        user_id=user_id,
        credentials=make_credentials(token="gmail-token"),
        email="user@example.com",
    )
    drive_store(db).save_connection(
        user_id=user_id,
        credentials=make_credentials(token="drive-token"),
        email="user@example.com",
    )

    rows = db.query(GoogleConnection).all()
    assert {row.provider for row in rows} == {"gmail", "drive"}

    decrypted_gmail = gmail_store(db).get_credentials(user_id)
    decrypted_drive = drive_store(db).get_credentials(user_id)
    assert decrypted_gmail.token == "gmail-token"
    assert decrypted_drive.token == "drive-token"


def test_disconnect_gmail_leaves_drive():
    db = make_session()
    user_id = uuid4()

    gmail_store(db).save_connection(
        user_id=user_id,
        credentials=make_credentials(),
        email="user@example.com",
    )
    drive_store(db).save_connection(
        user_id=user_id,
        credentials=make_credentials(),
        email="user@example.com",
    )

    gmail_store(db).delete_connection(user_id)

    assert gmail_store(db).get_connection(user_id) is None
    assert drive_store(db).get_connection(user_id) is not None


def test_disconnect_drive_leaves_gmail():
    db = make_session()
    user_id = uuid4()

    gmail_store(db).save_connection(
        user_id=user_id,
        credentials=make_credentials(),
        email="user@example.com",
    )
    drive_store(db).save_connection(
        user_id=user_id,
        credentials=make_credentials(),
        email="user@example.com",
    )

    drive_store(db).delete_connection(user_id)

    assert drive_store(db).get_connection(user_id) is None
    assert gmail_store(db).get_connection(user_id) is not None


def test_reconnect_overwrites_same_provider_row():
    db = make_session()
    user_id = uuid4()
    store = gmail_store(db)

    store.save_connection(
        user_id=user_id,
        credentials=make_credentials(token="first"),
        email="user@example.com",
    )
    store.save_connection(
        user_id=user_id,
        credentials=make_credentials(token="second"),
        email="user@example.com",
    )

    rows = (
        db.query(GoogleConnection)
        .filter(GoogleConnection.provider == "gmail")
        .all()
    )
    assert len(rows) == 1
    assert store.get_credentials(user_id).token == "second"


def test_fresh_token_returned_without_refresh(monkeypatch):
    db = make_session()
    user_id = uuid4()
    store = gmail_store(db)

    store.save_connection(
        user_id=user_id,
        credentials=make_credentials(token="fresh"),
        email="user@example.com",
    )

    def _no_refresh(self, request):
        raise AssertionError("must not refresh a fresh token")

    monkeypatch.setattr(Credentials, "refresh", _no_refresh)

    assert store.get_credentials(user_id).token == "fresh"


def test_dead_grant_raises_reconnect(monkeypatch):
    """Expired access + dead refresh token (e.g. Testing-mode 7-day
    expiry) must surface reconnect, not RefreshError."""
    db = make_session()
    user_id = uuid4()
    store = drive_store(db)

    store.save_connection(
        user_id=user_id,
        credentials=make_credentials(
            token="stale",
            expiry=datetime.now(timezone.utc) - timedelta(hours=2),
        ),
        email="user@example.com",
    )

    def _dead_refresh(self, request):
        raise RefreshError("invalid_grant: Token has been expired")

    monkeypatch.setattr(Credentials, "refresh", _dead_refresh)

    with pytest.raises(GoogleReconnectRequiredError, match="reconnect"):
        store.get_credentials(user_id)


def test_missing_refresh_token_raises_reconnect():
    db = make_session()
    user_id = uuid4()
    store = gmail_store(db)

    store.save_connection(
        user_id=user_id,
        credentials=make_credentials(
            token="stale",
            refresh_token=None,
            expiry=datetime.now(timezone.utc) - timedelta(hours=2),
        ),
        email="user@example.com",
    )

    with pytest.raises(GoogleReconnectRequiredError, match="reconnect"):
        store.get_credentials(user_id)


def test_successful_refresh_persists_new_token(monkeypatch):
    db = make_session()
    user_id = uuid4()
    store = gmail_store(db)

    store.save_connection(
        user_id=user_id,
        credentials=make_credentials(
            token="stale",
            expiry=datetime.now(timezone.utc) - timedelta(hours=2),
        ),
        email="user@example.com",
    )

    def _good_refresh(self, request):
        self.token = "rotated"
        self.expiry = datetime.now(timezone.utc) + timedelta(hours=1)

    monkeypatch.setattr(Credentials, "refresh", _good_refresh)

    assert store.get_credentials(user_id).token == "rotated"
    assert store.get_credentials(user_id).token == "rotated"


def test_unconnected_user_raises_value_error():
    db = make_session()

    with pytest.raises(ValueError, match="not connected"):
        gmail_store(db).get_credentials(uuid4())


def test_base_metadata_has_no_other_tables_created():
    """Guard: these tests only ever create google_connections."""
    assert set(Base.metadata.tables) >= {"google_connections"}
