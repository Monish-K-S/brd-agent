from datetime import datetime, timezone
from uuid import UUID

import requests
from app.core.config import settings
from app.core.token_crypto import (
    decrypt_token_or_legacy,
    encrypt_token,
)
from app.db.models.google_connection import GoogleConnection
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"


class GoogleReconnectRequiredError(ValueError):
    """The stored grant is dead (refresh token expired/revoked) and the
    user must reconnect. Routes translate this to a 409 carrying
    {"reconnect_required": True, "connector": ...} — never a 401, which
    the client reserves for Supabase session refresh."""


class GoogleOAuthStore:
    """Per-connector Google OAuth token storage.

    Gmail and Drive each own their google_connections row (provider
    "gmail" vs "drive"), so connecting/disconnecting one never touches
    the other. Moved verbatim out of GmailService; behavior identical
    apart from the provider filter and the reconnect error below.
    """

    def __init__(
        self,
        db: Session,
        provider: str,
        scopes: list[str],
    ):
        self.db = db
        self.provider = provider
        self.scopes = scopes

    def _normalize_expiry(
        self,
        expires_at: datetime | None,
    ) -> datetime | None:
        if expires_at is None:
            return None

        if expires_at.tzinfo is None:
            return expires_at.replace(
                tzinfo=timezone.utc,
            )

        return expires_at.astimezone(
            timezone.utc,
        )

    def _is_expired(
        self,
        expires_at: datetime | None,
    ) -> bool:
        if expires_at is None:
            return False

        normalized_expiry = self._normalize_expiry(
            expires_at,
        )

        if normalized_expiry is None:
            return False

        return normalized_expiry <= datetime.now(
            timezone.utc,
        )

    def save_connection(
        self,
        user_id: UUID,
        credentials: Credentials,
        email: str,
    ) -> GoogleConnection:
        connection = (
            self.db.query(GoogleConnection)
            .filter(
                GoogleConnection.user_id == user_id,
                GoogleConnection.provider == self.provider,
            )
            .first()
        )

        expires_at = self._normalize_expiry(
            credentials.expiry,
        )

        if connection is None:
            connection = GoogleConnection(
                user_id=user_id,
                provider=self.provider,
                email=email,
                access_token=encrypt_token(credentials.token),
                refresh_token=(
                    encrypt_token(credentials.refresh_token)
                    if credentials.refresh_token
                    else None
                ),
                expires_at=expires_at,
            )

            self.db.add(connection)

        else:
            connection.email = email
            connection.access_token = encrypt_token(credentials.token)

            if credentials.refresh_token:
                connection.refresh_token = encrypt_token(
                    credentials.refresh_token
                )

            connection.expires_at = expires_at

        self.db.commit()
        self.db.refresh(connection)

        return connection

    def get_connection(
        self,
        user_id: UUID,
    ) -> GoogleConnection | None:
        return (
            self.db.query(GoogleConnection)
            .filter(
                GoogleConnection.user_id == user_id,
                GoogleConnection.provider == self.provider,
            )
            .first()
        )

    def revoke_connection(
        self,
        user_id: UUID,
    ) -> bool:
        connection = self.get_connection(user_id)

        if connection is None:
            return False

        plaintext_refresh = (
            decrypt_token_or_legacy(connection.refresh_token)[0]
            if connection.refresh_token
            else None
        )
        plaintext_access, _ = decrypt_token_or_legacy(
            connection.access_token
        )

        for token in (
            plaintext_refresh,
            plaintext_access,
        ):
            if not token:
                continue

            try:
                response = requests.post(
                    GOOGLE_REVOKE_URL,
                    data={"token": token},
                    timeout=5,
                )

                if response.status_code == 200:
                    return True
            except requests.RequestException:
                continue

        return False

    def delete_connection(
        self,
        user_id: UUID,
    ) -> None:
        connection = self.get_connection(user_id)

        if connection is None:
            return

        self.db.delete(connection)
        self.db.commit()

    def get_credentials(
        self,
        user_id: UUID,
    ) -> Credentials:
        connection = self.get_connection(user_id)

        if connection is None:
            raise ValueError("Google account is not connected.")

        expires_at = self._normalize_expiry(
            connection.expires_at,
        )

        # IMPORTANT:
        # Do not use credentials.expired here.
        #
        # google-auth versions can internally compare
        # timezone-naive and timezone-aware datetimes.
        # We perform the comparison ourselves instead.
        token_expired = self._is_expired(
            expires_at,
        )

        access_token, access_encrypted = decrypt_token_or_legacy(
            connection.access_token
        )

        if connection.refresh_token:
            refresh_token, refresh_encrypted = decrypt_token_or_legacy(
                connection.refresh_token
            )
        else:
            refresh_token, refresh_encrypted = None, True

        if not access_encrypted or not refresh_encrypted:
            connection.access_token = encrypt_token(access_token)

            if refresh_token:
                connection.refresh_token = encrypt_token(refresh_token)

            self.db.commit()

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=self.scopes,
            expiry=None,
        )

        if token_expired:
            if not refresh_token:
                raise GoogleReconnectRequiredError(
                    "Google access token has expired and "
                    "no refresh token is available. "
                    "Please reconnect Google."
                )

            try:
                credentials.refresh(Request())
            except RefreshError as exc:
                # Dead grant: Testing-mode refresh tokens die after
                # 7 days, users revoke access, passwords change.
                # Surface "reconnect" instead of a 500/400 blob.
                raise GoogleReconnectRequiredError(
                    "Google connection has expired. "
                    "Please reconnect Google."
                ) from exc

            connection.access_token = encrypt_token(credentials.token)

            if credentials.expiry is not None:
                connection.expires_at = self._normalize_expiry(
                    credentials.expiry,
                )

            self.db.commit()

        return credentials
