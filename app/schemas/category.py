import uuid
from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=3, max_length=255)
    user_id: uuid.UUID


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=3, max_length=255)


class CategoryRead(CategoryBase):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)


class CategoryResponse(BaseModel):
    message: str
    category: CategoryRead


class CategoryListResponse(BaseModel):
    message: str
    categories: list[CategoryRead]  


class CategoryDeleteResponse(BaseModel):
    message: str