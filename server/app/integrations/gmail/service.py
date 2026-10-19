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

    def get_messages(
        self,
        user_id: UUID,
        message_ids: list[str],
    ) -> list[dict]:
        """Fetch several messages in one HTTP round trip (L-9).

        The browse/search routes used to call ``get_message`` per id, and
        every call re-read credentials (DB + Fernet, sometimes a refresh)
        and rebuilt the discovery client — up to 20 serial round trips
        plus 42 setup calls. Here credentials and client are built **once**
        and every ``messages.get`` rides a single
        ``new_batch_http_request``: two calls total.

        Results come back in the order of ``message_ids``. A failed
        sub-response propagates, exactly as the old loop's exception did
        (routes map it to 400 — no behavior change). If the batch request
        itself fails, the same ids are fetched sequentially on the **same**
        built client, so batch trouble degrades to slower rather than
        broken, and credentials are still read only once.
        """
        if not message_ids:
            return []

        credentials = self.get_credentials(user_id)

        from googleapiclient.discovery import build

        gmail = build(
            "gmail",
            "v1",
            credentials=credentials,
        )

        results: dict[str, dict] = {}
        failures: dict[str, Exception] = {}

        def collect(request_id, response, exception):
            if exception is not None:
                failures[request_id] = exception
            else:
                results[request_id] = response

        try:
            batch = gmail.new_batch_http_request(
                callback=collect,
            )

            for message_id in message_ids:
                batch.add(
                    gmail.users()
                    .messages()
                    .get(
                        userId="me",
                        id=message_id,
                        format="full",
                    ),
                    request_id=message_id,
                )

            batch.execute()
        except Exception:
            return [
                gmail.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="full",
                )
                .execute()
                for message_id in message_ids
            ]

        ordered: list[dict] = []

        for message_id in message_ids:
            if message_id in failures:
                raise failures[message_id]

            ordered.append(results[message_id])

        return ordered
