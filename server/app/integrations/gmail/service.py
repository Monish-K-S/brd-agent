from datetime import datetime, timezone
from uuid import UUID

import requests
from app.core.config import settings
from app.core.token_crypto import (
    decrypt_token_or_legacy,
    encrypt_token,
)
from app.db.models.google_connection import GoogleConnection
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"


GOOGLE_SCOPES = [
    GMAIL_READONLY_SCOPE,
]


class GmailService:
    def __init__(self, db: Session):
        self.db = db

    def _create_flow(
        self,
        state: str | None = None,
        code_verifier: str | None = None,
    ) -> Flow:
        client_config = {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [
                    settings.google_redirect_uri,
                ],
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=GOOGLE_SCOPES,
            state=state,
        )

        flow.redirect_uri = settings.google_redirect_uri

        if code_verifier:
            flow.code_verifier = code_verifier

        return flow

    def create_authorization_url(
        self,
        state: str,
        code_verifier: str,
    ) -> str:
        flow = self._create_flow(
            state=state,
            code_verifier=code_verifier,
        )

        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )

        return authorization_url

    def exchange_code(
        self,
        code: str,
        state: str,
        code_verifier: str,
    ) -> Credentials:
        flow = self._create_flow(
            state=state,
            code_verifier=code_verifier,
        )

        flow.fetch_token(
            code=code,
        )

        return flow.credentials

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
                GoogleConnection.provider == "google",
            )
            .first()
        )

        expires_at = self._normalize_expiry(
            credentials.expiry,
        )

        if connection is None:
            connection = GoogleConnection(
                user_id=user_id,
                provider="google",
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
                GoogleConnection.provider == "google",
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
            scopes=GOOGLE_SCOPES,
            expiry=None,
        )

        if token_expired:
            if not refresh_token:
                raise ValueError(
                    "Google access token has expired and "
                    "no refresh token is available. "
                    "Please reconnect Google."
                )

            credentials.refresh(Request())

            connection.access_token = encrypt_token(credentials.token)

            if credentials.expiry is not None:
                connection.expires_at = self._normalize_expiry(
                    credentials.expiry,
                )

            self.db.commit()

        return credentials

    def list_messages(
        self,
        user_id: UUID,
        query: str | None = None,
        max_results: int = 5,
    ) -> list[dict]:
        credentials = self.get_credentials(user_id)

        from googleapiclient.discovery import build

        gmail = build(
            "gmail",
            "v1",
            credentials=credentials,
        )

        request = (
            gmail.users()
            .messages()
            .list(
                userId="me",
                maxResults=max_results,
            )
        )

        if query:
            request = (
                gmail.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=max_results,
                )
            )

        response = request.execute()

        return response.get(
            "messages",
            [],
        )

    def get_message(
        self,
        user_id: UUID,
        message_id: str,
    ) -> dict:
        credentials = self.get_credentials(user_id)

        from googleapiclient.discovery import build

        gmail = build(
            "gmail",
            "v1",
            credentials=credentials,
        )

        return (
            gmail.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="full",
            )
            .execute()
        )
