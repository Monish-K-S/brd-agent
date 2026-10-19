import io
from uuid import UUID

from app.core.config import settings
from app.integrations.google_oauth_store import GoogleOAuthStore
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.http import MediaIoBaseDownload
from sqlalchemy.orm import Session


DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"


# Drive grants are drive.file-only: a Drive connect no longer carries
# Gmail read access, and the Drive row is fully independent of Gmail's.
DRIVE_SCOPES = [
    DRIVE_FILE_SCOPE,
]

DRIVE_PROVIDER = "drive"


# Drive MIME types that download as raw bytes and flow through the
# existing parser factory (.pdf -> PdfParser, .docx -> DocxParser,
# .txt -> TxtParser). Google-native files (application/vnd.google-apps.*)
# require export and are rejected by the import service.
DRIVE_DOWNLOAD_MIMETYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
        ".docx"
    ),
    "text/plain": ".txt",
}


class DriveService:
    """
    Google Drive API access for the Drive source connector.

    Token storage, encryption, and refresh live in GoogleOAuthStore
    scoped to provider="drive", so the Drive grant is fully independent
    of the Gmail grant. Only the OAuth flow (redirect URI + scopes) and
    the Drive API calls live here.
    """

    def __init__(self, db: Session):
        self.db = db
        self.oauth_store = GoogleOAuthStore(
            db,
            provider=DRIVE_PROVIDER,
            scopes=DRIVE_SCOPES,
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
                    settings.google_drive_redirect_uri,
                ],
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=DRIVE_SCOPES,
            state=state,
        )

        flow.redirect_uri = settings.google_drive_redirect_uri

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

    def get_connection(
        self,
        user_id: UUID,
    ):
        return self.oauth_store.get_connection(user_id)

    def save_connection(
        self,
        user_id: UUID,
        credentials: Credentials,
        email: str,
    ):
        return self.oauth_store.save_connection(
            user_id=user_id,
            credentials=credentials,
            email=email,
        )

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

    def get_picker_token(
        self,
        user_id: UUID,
    ) -> str:
        # get_credentials refreshes the access token when expired,
        # so the returned token is always usable by the Picker.
        credentials = self.get_credentials(user_id)

        if not credentials.token:
            raise ValueError("Google account is not connected.")

        return credentials.token

    def _drive_client(
        self,
        user_id: UUID,
    ):
        credentials = self.get_credentials(user_id)

        from googleapiclient.discovery import build

        return build(
            "drive",
            "v3",
            credentials=credentials,
        )

    def get_file_metadata(
        self,
        user_id: UUID,
        file_id: str,
    ) -> dict:
        drive = self._drive_client(user_id)

        return (
            drive.files()
            .get(
                fileId=file_id,
                fields="id,name,mimeType,size,modifiedTime,webViewLink",
            )
            .execute()
        )

    def download_file(
        self,
        user_id: UUID,
        file_id: str,
        max_bytes: int | None = None,
    ) -> bytes:
        """
        Download a Drive file as bytes, aborting as soon as the byte
        ceiling is exceeded.

        The download is streamed chunk-by-chunk instead of buffered with
        a single `.execute()`, so an oversized (or mis-declared) file is
        rejected without ever being fully resident in memory. The
        metadata size field is advisory only and cannot be trusted to
        bound the transfer.
        """

        drive = self._drive_client(user_id)

        limit = (
            max_bytes
            if max_bytes is not None
            else settings.max_upload_bytes
        )

        request = drive.files().get_media(
            fileId=file_id,
        )

        buffer = io.BytesIO()

        downloader = MediaIoBaseDownload(
            buffer,
            request,
            chunksize=256 * 1024,
        )

        done = False

        while not done:
            _, done = downloader.next_chunk()

            if buffer.tell() > limit:
                raise ValueError(
                    "File too large: maximum file size is "
                    f"{limit // (1024 * 1024)} MB."
                )

        return buffer.getvalue()
