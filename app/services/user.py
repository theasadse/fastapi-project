from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self) -> None:
        self._users: list[User] = []
        self._next_id = 1

    def list_users(self) -> list[User]:
        return self._users

    def get_user(self, user_id: int) -> User:
        user = next((item for item in self._users if item.id == user_id), None)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    def create_user(self, payload: UserCreate) -> User:
        self._ensure_email_is_unique(payload.email)
        user = User(id=self._next_id, **payload.model_dump())
        self._users.append(user)
        self._next_id += 1
        return user

    def update_user(self, user_id: int, payload: UserUpdate) -> User:
        user = self.get_user(user_id)
        updates = payload.model_dump(exclude_unset=True)

        if "email" in updates:
            self._ensure_email_is_unique(updates["email"], excluded_user_id=user_id)

        for field, value in updates.items():
            setattr(user, field, value)

        return user

    def delete_user(self, user_id: int) -> None:
        user = self.get_user(user_id)
        self._users.remove(user)

    def _ensure_email_is_unique(
        self,
        email: str,
        excluded_user_id: int | None = None,
    ) -> None:
        email_in_use = any(
            user.email == email and user.id != excluded_user_id for user in self._users
        )
        if email_in_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )


user_service = UserService()
