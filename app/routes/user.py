from fastapi import APIRouter, Response, status

from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.user import user_service


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserRead])
def list_users() -> list[UserRead]:
    return user_service.list_users()


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int) -> UserRead:
    return user_service.get_user(user_id)


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate) -> UserRead:
    return user_service.create_user(payload)


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate) -> UserRead:
    return user_service.update_user(user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int) -> Response:
    user_service.delete_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
