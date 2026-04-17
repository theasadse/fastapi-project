import hashlib
import hmac
import os
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserUpdate


class UserService:
    def list_users(self, db: Session) -> list[User]:
        return list(db.scalars(select(User)).all())

    def get_user(self, db: Session, user_id: uuid.UUID) -> User:
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    def create_user(self, db: Session, payload: UserCreate) -> User:
        self._ensure_username_is_unique(db, payload.username)
        self._ensure_email_is_unique(db, payload.email)
        user_data = payload.model_dump(exclude={"password"})
        user = User(
            **user_data,
            password_hash=self._hash_password(payload.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update_user(self, db: Session, user_id: uuid.UUID, payload: UserUpdate) -> User:
        user = self.get_user(db, user_id)
        updates = payload.model_dump(exclude_unset=True)

        if "username" in updates:
            self._ensure_username_is_unique(
                db,
                updates["username"],
                excluded_user_id=user_id,
            )

        if "email" in updates:
            self._ensure_email_is_unique(
                db,
                updates["email"],
                excluded_user_id=user_id,
            )

        password = updates.pop("password", None)
        for field, value in updates.items():
            setattr(user, field, value)

        if password is not None:
            user.password_hash = self._hash_password(password)

        db.commit()
        db.refresh(user)
        return user

    def login_user(self, db: Session, payload: UserLogin) -> User:
        user = db.scalar(select(User).where(User.email == payload.email))
        if user is None or not self._verify_password(
            payload.password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        return user

    def delete_user(self, db: Session, user_id: uuid.UUID) -> None:
        user = self.get_user(db, user_id)
        db.delete(user)
        db.commit()

    def _ensure_username_is_unique(
        self,
        db: Session,
        username: str,
        excluded_user_id: uuid.UUID | None = None,
    ) -> None:
        existing_user = db.scalar(select(User).where(User.username == username))
        username_in_use = (
            existing_user is not None and existing_user.id != excluded_user_id
        )
        if username_in_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )

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

    def _hash_password(self, password: str) -> str:
        salt = os.urandom(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return f"{salt.hex()}:{hashed.hex()}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        try:
            salt_hex, hash_hex = password_hash.split(":")
            salt = bytes.fromhex(salt_hex)
            expected_hash = bytes.fromhex(hash_hex)
        except ValueError:
            return False

        password_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            100_000,
        )
        return hmac.compare_digest(password_digest, expected_hash)


user_service = UserService()
