import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from app.auth.dependencies import CurrentUser, get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.integrations.gmail.service import GmailService
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/integrations/gmail",
    tags=["Gmail"],
)


STATE_EXPIRATION_MINUTES = 10


def create_oauth_state(
    user_id: UUID,
    code_verifier: str,
) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
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
) -> tuple[UUID, str]:
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

        user_id = UUID(
            payload["sub"],
        )

        code_verifier = payload.get(
            "code_verifier",
        )

        if not code_verifier:
            raise HTTPException(
                status_code=400,
                detail="Invalid OAuth state.",
            )

        return user_id, code_verifier

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
def connect_gmail(
    current_user: CurrentUser = Depends(
        get_current_user,
    ),
    db: Session = Depends(get_db),
):
    code_verifier = secrets.token_urlsafe(64)

    state = create_oauth_state(
        user_id=current_user.id,
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
    user_id, code_verifier = verify_oauth_state(
        state,
    )

    gmail_service = GmailService(db)

    try:
        credentials = gmail_service.exchange_code(
            code=code,
            state=state,
            code_verifier=code_verifier,
        )

        email = get_google_account_email(
            credentials,
        )

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

    return {
        "status": "connected",
        "email": email,
    }


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
