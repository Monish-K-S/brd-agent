import secrets
import threading
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from app.auth.dependencies import CurrentUser, get_current_user
from app.core.audit import audit
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.integrations.drive.import_service import DriveImportService
from app.integrations.google_oauth_store import GoogleReconnectRequiredError
from app.integrations.drive.schemas import (
    DriveFileImportRequest,
    DriveFileImportResponse,
    DriveImportedDocument,
)
from app.integrations.drive.service import DriveService
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/integrations/drive",
    tags=["Google Drive"],
)


STATE_EXPIRATION_MINUTES = 10

# Single-use PKCE verifier store, keyed by state JWT ID.
# NOTE: in-memory by design (consistent with the in-memory rate limiter
# and the Gmail connector); entries do not survive restarts and are not
# shared across workers. Separate store from Gmail so the two connects
# cannot consume each other's states.
_oauth_verifiers: dict[
    str,
    tuple[UUID, UUID, str, datetime],
] = {}

_oauth_verifiers_lock = threading.Lock()


def _purge_expired_verifiers(now: datetime) -> None:
    expired = [
        jti
        for jti, (_, _, _, expires_at) in _oauth_verifiers.items()
        if expires_at <= now
    ]

    for jti in expired:
        del _oauth_verifiers[jti]


def create_oauth_state(
    user_id: UUID,
    workspace_id: UUID,
    code_verifier: str,
) -> str:
    now = datetime.now(timezone.utc)
    jti = secrets.token_urlsafe(16)

    payload = {
        "sub": str(user_id),
        "workspace_id": str(workspace_id),
        "purpose": "drive_connect",
        "jti": jti,
        "iat": now,
        "exp": now
        + timedelta(
            minutes=STATE_EXPIRATION_MINUTES,
        ),
    }

    state = jwt.encode(
        payload,
        settings.oauth_state_secret,
        algorithm="HS256",
    )

    with _oauth_verifiers_lock:
        _purge_expired_verifiers(now)

        _oauth_verifiers[jti] = (
            user_id,
            workspace_id,
            code_verifier,
            now
            + timedelta(
                minutes=STATE_EXPIRATION_MINUTES,
            ),
        )

    return state


def verify_oauth_state(
    state: str,
) -> tuple[UUID, UUID, str]:
    try:
        payload = jwt.decode(
            state,
            settings.oauth_state_secret,
            algorithms=["HS256"],
        )

        if payload.get("purpose") != "drive_connect":
            raise HTTPException(
                status_code=400,
                detail="Invalid OAuth state.",
            )

        user_id = UUID(
            payload["sub"],
        )

        workspace_id = UUID(
            payload["workspace_id"],
        )

        jti = payload.get("jti")

        if not jti:
            raise HTTPException(
                status_code=400,
                detail="Invalid OAuth state.",
            )

        now = datetime.now(timezone.utc)

        with _oauth_verifiers_lock:
            entry = _oauth_verifiers.pop(jti, None)

            _purge_expired_verifiers(now)

        if entry is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OAuth state.",
            )

        _, _, code_verifier, expires_at = entry

        if expires_at <= now:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OAuth state.",
            )

        return (
            user_id,
            workspace_id,
            code_verifier,
        )

    except HTTPException:
        raise
    except (
        jwt.PyJWTError,
        KeyError,
        ValueError,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OAuth state.",
        )


@router.get("/connect")
@limiter.limit(settings.rate_limit_drive_connect)
def connect_drive(
    request: Request,
    workspace_id: UUID = Query(...),
    current_user: CurrentUser = Depends(
        get_current_user,
    ),
    db: Session = Depends(get_db),
):
    code_verifier = secrets.token_urlsafe(64)

    state = create_oauth_state(
        user_id=current_user.id,
        workspace_id=workspace_id,
        code_verifier=code_verifier,
    )

    drive_service = DriveService(db)

    authorization_url = drive_service.create_authorization_url(
        state=state,
        code_verifier=code_verifier,
    )

    audit(
        event="drive.connect",
        outcome="started",
        user_id=current_user.id,
        workspace_id=workspace_id,
    )

    return {
        "authorization_url": authorization_url,
    }


@router.get("/callback")
@limiter.limit(settings.rate_limit_drive_callback)
def drive_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    (
        user_id,
        workspace_id,
        code_verifier,
    ) = verify_oauth_state(state)

    drive_service = DriveService(db)

    try:
        credentials = drive_service.exchange_code(
            code=code,
            state=state,
            code_verifier=code_verifier,
        )

        drive_service.save_connection(
            user_id=user_id,
            credentials=credentials,
            email=_get_account_email(credentials),
        )

    except Exception as exc:
        db.rollback()

        audit(
            event="drive.connect",
            outcome="failed",
            user_id=user_id,
            workspace_id=workspace_id,
        )

        raise HTTPException(
            status_code=400,
            detail=f"Unable to connect Google Drive: {exc}",
        )

    audit(
        event="drive.connect",
        outcome="success",
        user_id=user_id,
        workspace_id=workspace_id,
    )

    return RedirectResponse(
        url=(f"{settings.frontend_url}/workspaces/{workspace_id}"),
        status_code=303,
    )


def _get_account_email(
    credentials,
) -> str:
    from googleapiclient.discovery import build

    drive = build(
        "drive",
        "v3",
        credentials=credentials,
    )

    about = (
        drive.about()
        .get(
            fields="user",
        )
        .execute()
    )

    email = (about.get("user") or {}).get("emailAddress")

    if not email:
        raise ValueError("Unable to determine Google account email.")

    return email


@router.get("/status")
def drive_status(
    current_user: CurrentUser = Depends(
        get_current_user,
    ),
    db: Session = Depends(get_db),
):
    drive_service = DriveService(db)

    connection = drive_service.get_connection(
        current_user.id,
    )

    if connection is None:
        return {
            "connected": False,
            "email": None,
        }

    return {
        "connected": True,
        "email": connection.email,
    }


@router.delete("")
def disconnect_drive(
    current_user: CurrentUser = Depends(
        get_current_user,
    ),
    db: Session = Depends(get_db),
):
    drive_service = DriveService(db)

    revoked = drive_service.revoke_connection(
        current_user.id,
    )

    drive_service.delete_connection(
        current_user.id,
    )

    audit(
        event="drive.disconnect",
        outcome="success" if revoked else "revoke_failed",
        user_id=current_user.id,
    )

    return {
        "status": "disconnected",
    }


@router.get("/picker-token")
@limiter.limit(settings.rate_limit_drive_picker_token)
def drive_picker_token(
    request: Request,
    current_user: CurrentUser = Depends(
        get_current_user,
    ),
    db: Session = Depends(get_db),
):
    drive_service = DriveService(db)

    try:
        access_token = drive_service.get_picker_token(
            user_id=current_user.id,
        )

        return {
            "access_token": access_token,
        }

    except GoogleReconnectRequiredError as exc:
        # Dead grant (expired/revoked refresh token): the Picker must
        # offer "Reconnect", not a cryptic open failure. 409, never 401
        # — the client reserves 401 for Supabase session refresh.
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(exc),
                "reconnect_required": True,
                "connector": "drive",
            },
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=(f"Unable to issue Drive picker token: {exc}"),
        )


@router.post(
    "/workspaces/{workspace_id}/files/import",
    response_model=DriveFileImportResponse,
)
@limiter.limit(settings.rate_limit_drive_import)
def import_drive_file(
    request: Request,
    workspace_id: UUID,
    import_request: DriveFileImportRequest,
    current_user: CurrentUser = Depends(
        get_current_user,
    ),
    db: Session = Depends(get_db),
):
    import_service = DriveImportService(db)

    try:
        (
            created_documents,
            skipped_file_ids,
        ) = import_service.import_files(
            workspace_id=workspace_id,
            user_id=current_user.id,
            drive_file_ids=import_request.drive_file_ids,
        )

        imported = [
            DriveImportedDocument(
                id=document.id,
                drive_file_id=document.metadata_.get(
                    "drive_file_id",
                    "",
                ),
                title=document.title,
            )
            for document in created_documents
        ]

        return DriveFileImportResponse(
            imported=imported,
            skipped_file_ids=skipped_file_ids,
        )

    except GoogleReconnectRequiredError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(exc),
                "reconnect_required": True,
                "connector": "drive",
            },
        )

    except ValueError as exc:
        message = str(exc)

        if "too large" in message.lower():
            raise HTTPException(
                status_code=413,
                detail=message,
            )

        raise HTTPException(
            status_code=400,
            detail=message,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=(f"Unable to import Drive file: {exc}"),
        )
