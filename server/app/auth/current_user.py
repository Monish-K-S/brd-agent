from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.services.user_service import UserService


def get_current_db_user(
    current_user: Annotated[
        CurrentUser,
        Depends(get_current_user),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
) -> User:
    user_service = UserService(db)

    return user_service.ensure_user_exists(
        current_user,
    )
