import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from app.auth.dependencies import CurrentUser, get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.integrations.gmail.import_service import GmailImportService
from app.integrations.gmail.mapper import GmailEmailMapper
from app.integrations.gmail.schemas import (
    GmailImportedDocument,
    GmailImportRequest,
    GmailImportResponse,
    GmailMessageListResponse,
)
from app.integrations.gmail.service import GmailService
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/integrations/gmail",
    tags=["Gmail"],
)


STATE_EXPIRATION_MINUTES = 10


def create_oauth_state(
    user_id: UUID,
    workspace_id: UUID,
    code_verifier: str,
) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "workspace_id": str(workspace_id),
        "purpose": "gmail_connect",
        "code_verifier": code_verifier,
        "iat": now,
        "exp": now
        + timedelta(
            minutes=STATE_EXPIRATION_MINUTES,
        ),
    }

    return jwt.encode(
        payload,
        settings.google_client_secret,
        algorithm="HS256",
    )


def verify_oauth_state(
    state: str,
) -> tuple[UUID, UUID, str]:
    try:
        payload = jwt.decode(
            state,
            settings.google_client_secret,
            algorithms=["HS256"],
        )

        if payload.get("purpose") != "gmail_connect":
            raise HTTPException(
                status_code=400,
                detail="Invalid OAuth state.",
            )

        user_id = UUID(payload["sub"])
        workspace_id = UUID(payload["workspace_id"])

        code_verifier = payload.get("code_verifier")

        if not code_verifier:
            raise HTTPException(
                status_code=400,
                detail="Invalid OAuth state.",
            )

        return user_id, workspace_id, code_verifier

    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OAuth state.",
        )


@router.get("/connect")
def connect_gmail(
    workspace_id: UUID = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    code_verifier = secrets.token_urlsafe(64)

    state = create_oauth_state(
        user_id=current_user.id,
        workspace_id=workspace_id,
        code_verifier=code_verifier,
    )

    gmail_service = GmailService(db)

    authorization_url = gmail_service.create_authorization_url(
        state=state,
        code_verifier=code_verifier,
    )

    return {
        "authorization_url": authorization_url,
    }


@router.get("/callback")
def gmail_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    user_id, workspace_id, code_verifier = verify_oauth_state(
        state,
    )

    gmail_service = GmailService(db)

    try:
        credentials = gmail_service.exchange_code(
            code=code,
            state=state,
            code_verifier=code_verifier,
        )

        email = get_google_account_email(credentials)

        gmail_service.save_connection(
            user_id=user_id,
            email=email,
            credentials=credentials,
        )

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=f"Unable to connect Gmail: {exc}",
        )

    return RedirectResponse(
        url=f"{settings.frontend_url}/workspaces/{workspace_id}",
        status_code=303,
    )


def get_google_account_email(
    credentials,
) -> str:
    from googleapiclient.discovery import build

    gmail = build(
        "gmail",
        "v1",
        credentials=credentials,
    )

    profile = (
        gmail.users()
        .getProfile(
            userId="me",
        )
        .execute()
    )

    email = profile.get(
        "emailAddress",
    )

    if not email:
        raise ValueError("Unable to determine Gmail account email.")

    return email


@router.get("/status")
def gmail_status(
    current_user: CurrentUser = Depends(
        get_current_user,
    ),
    db: Session = Depends(get_db),
):
    gmail_service = GmailService(db)

    connection = gmail_service.get_connection(
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
def disconnect_gmail(
    current_user: CurrentUser = Depends(
        get_current_user,
    ),
    db: Session = Depends(get_db),
):
    gmail_service = GmailService(db)

    gmail_service.delete_connection(
        current_user.id,
    )

    return {
        "status": "disconnected",
    }


@router.get(
    "/messages/recent",
    response_model=GmailMessageListResponse,
)
def recent_gmail_messages(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    gmail_service = GmailService(db)
    mapper = GmailEmailMapper()

    try:
        messages = gmail_service.list_messages(
            user_id=current_user.id,
            max_results=5,
        )

        summaries = [mapper.to_message_summary(message) for message in messages]

        return {
            "messages": summaries,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to retrieve Gmail messages: {exc}",
        )


@router.get(
    "/messages/search",
    response_model=GmailMessageListResponse,
)
def search_gmail_messages(
    q: str = Query(..., min_length=1),
    max_results: int = Query(
        default=5,
        ge=1,
        le=20,
    ),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    gmail_service = GmailService(db)
    mapper = GmailEmailMapper()

    try:
        messages = gmail_service.list_messages(
            user_id=current_user.id,
            query=q,
            max_results=max_results,
        )

        summaries = [mapper.to_message_summary(message) for message in messages]

        return {
            "messages": summaries,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to search Gmail messages: {exc}",
        )


@router.post(
    "/workspaces/{workspace_id}/messages/import",
    response_model=GmailImportResponse,
)
def import_gmail_messages(
    workspace_id: UUID,
    request: GmailImportRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import_service = GmailImportService(db)

    try:
        created_documents, skipped_message_ids = import_service.import_messages(
            workspace_id=workspace_id,
            user_id=current_user.id,
            message_ids=request.message_ids,
        )

        imported = [
            GmailImportedDocument(
                id=document.id,
                gmail_message_id=document.metadata_.get(
                    "gmail_message_id",
                    "",
                ),
                title=document.title,
            )
            for document in created_documents
        ]

        return GmailImportResponse(
            imported=imported,
            skipped_message_ids=skipped_message_ids,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to import Gmail messages: {exc}",
        )
