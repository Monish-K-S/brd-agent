from uuid import UUID

from app.core.config import settings
from app.db.models.google_connection import GoogleConnection
from app.integrations.google_oauth_store import GoogleOAuthStore
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


GOOGLE_SCOPES = [
    GMAIL_READONLY_SCOPE,
]

GMAIL_PROVIDER = "gmail"


class GmailService:
    """Gmail API access for the Gmail source connector.

    Token storage, encryption, and refresh live in GoogleOAuthStore
    scoped to provider="gmail", so the Gmail grant is fully independent
    of the Drive grant. Only the OAuth flow (redirect URI + scopes) and
    the Gmail API calls live here.
    """

    def __init__(self, db: Session):
        self.db = db
        self.oauth_store = GoogleOAuthStore(
            db,
            provider=GMAIL_PROVIDER,
            scopes=GOOGLE_SCOPES,
        )

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

    def save_connection(
        self,
        user_id: UUID,
        credentials: Credentials,
        email: str,
    ) -> GoogleConnection:
        return self.oauth_store.save_connection(
            user_id=user_id,
            credentials=credentials,
            email=email,
        )

    def get_connection(
        self,
        user_id: UUID,
    ) -> GoogleConnection | None:
        return self.oauth_store.get_connection(user_id)

    def revoke_connection(
        self,
        user_id: UUID,
    ) -> bool:
        return self.oauth_store.revoke_connection(user_id)

    def delete_connection(
        self,
        user_id: UUID,
    ) -> None:
        self.oauth_store.delete_connection(user_id)

    def get_credentials(
        self,
        user_id: UUID,
    ) -> Credentials:
        return self.oauth_store.get_credentials(user_id)

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
