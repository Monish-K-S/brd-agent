from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.db.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, db: Session):
        self.db = db

        self.user_repository = UserRepository(db)


    def ensure_user_exists(
        self,
        current_user: CurrentUser,
    ) -> User:
        existing_user = self.user_repository.get_by_id(
            current_user.id,
        )

        if existing_user is not None:
            return existing_user

        user = User(
            id=current_user.id,
            email=current_user.email,
        )

        try:
            created_user = self.user_repository.create(
                user,
            )

            self.db.commit()

            return created_user

        except Exception:
            self.db.rollback()
            raise
