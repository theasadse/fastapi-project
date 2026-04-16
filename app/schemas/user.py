from pydantic import BaseModel, EmailStr
from pydantic import ConfigDict


class UserBase(BaseModel):
    name: str
    email: EmailStr


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None


class UserRead(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
