import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.user import UserRole

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    name: str
    email: EmailStr
    role: UserRole = UserRole.staff

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: UserRole | None = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRead(UserBase):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)

class LoginResponse(BaseModel):
    message: str
    user: UserRead