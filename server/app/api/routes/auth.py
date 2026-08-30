from fastapi import APIRouter, Depends

from app.auth.current_user import get_current_db_user
from app.db.models.user import User


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.get(
    "/me",
    response_model=None,
)
def get_me(
    current_user: User = Depends(
        get_current_db_user,
    ),
):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
    }
