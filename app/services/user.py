from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from fastapi import HTTPException, status


class UserService:
    def list_users(self, db: Session) -> list[User]:
        return list(db.scalars(select(User)).all())

    def get_user(self, db: Session, user_id: int) -> User:
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    def create_user(self, db: Session, payload: UserCreate) -> User:
        self._ensure_email_is_unique(db, payload.email)
        user = User(**payload.model_dump())
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update_user(self, db: Session, user_id: int, payload: UserUpdate) -> User:
        user = self.get_user(db, user_id)
        updates = payload.model_dump(exclude_unset=True)

        if "email" in updates:
            self._ensure_email_is_unique(
                db,
                updates["email"],
                excluded_user_id=user_id,
            )

        for field, value in updates.items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)
        return user

    def delete_user(self, db: Session, user_id: int) -> None:
        user = self.get_user(db, user_id)
        db.delete(user)
        db.commit()

    def _ensure_email_is_unique(
        self,
        db: Session,
        email: str,
        excluded_user_id: int | None = None,
    ) -> None:
        existing_user = db.scalar(select(User).where(User.email == email))
        email_in_use = (
            existing_user is not None and existing_user.id != excluded_user_id
        )
        if email_in_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )


user_service = UserService()
