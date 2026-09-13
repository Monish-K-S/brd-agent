from datetime import timezone
from uuid import UUID

from app.core.config import settings
from app.db.models.google_connection import GoogleConnection
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class GmailService:
    def __init__(self, db: Session):
        self.db = db

    def create_authorization_url(
        self,
        state: str,
        code_verifier: str,
    ) -> str:
        flow = self._create_flow(
            state=state,
        )

        flow.code_verifier = code_verifier

        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
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
        )

        flow.code_verifier = code_verifier

        flow.fetch_token(
            code=code,
        )

        credentials = flow.credentials

        if not credentials.refresh_token:
            raise ValueError("Google did not return a refresh token.")

        return credentials

    def _create_flow(
        self,
        state: str | None = None,
    ) -> Flow:
        client_config = {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": ("https://accounts.google.com/o/oauth2/auth"),
                "token_uri": ("https://oauth2.googleapis.com/token"),
                "redirect_uris": [
                    settings.google_redirect_uri,
                ],
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=[GMAIL_READONLY_SCOPE],
            state=state,
        )

        flow.redirect_uri = settings.google_redirect_uri

        return flow

    def save_connection(
        self,
        user_id: UUID,
        email: str,
        credentials: Credentials,
    ) -> GoogleConnection:
        connection = (
            self.db.query(GoogleConnection)
            .filter(
                GoogleConnection.user_id == user_id,
                GoogleConnection.provider == "google",
            )
            .first()
        )

        expires_at = credentials.expiry

        if expires_at is None:
            raise ValueError("Google credentials did not include an expiry time.")

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc,
            )

        if connection is None:
            connection = GoogleConnection(
                user_id=user_id,
                provider="google",
                email=email,
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                expires_at=expires_at,
            )

            self.db.add(connection)

        else:
            connection.email = email
            connection.access_token = credentials.token

            if credentials.refresh_token:
                connection.refresh_token = credentials.refresh_token

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

    def delete_connection(
        self,
        user_id: UUID,
    ) -> None:
        connection = self.get_connection(user_id)

        if connection is None:
            return

        self.db.delete(connection)
        self.db.commit()
