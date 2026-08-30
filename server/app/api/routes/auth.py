from fastapi import APIRouter, Depends

from app.auth.dependencies import (
    CurrentUser,
    get_current_user,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.get("/me")
def get_me(
    current_user: CurrentUser = Depends(
        get_current_user,
    ),
) -> CurrentUser:
    return current_user
