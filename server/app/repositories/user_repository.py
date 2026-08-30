from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        user_id: UUID,
    ) -> User | None:
        return self.db.get(
            User,
            user_id,
        )


    def create(
        self,
        user: User,
    ) -> User:
        self.db.add(user)
        self.db.flush()

        return user
