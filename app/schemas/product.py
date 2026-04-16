from pydantic import BaseModel, ConfigDict, Field

class ProductBase(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=3, max_length=255)
    price: float = Field(gt=0)
    stock: int = Field(ge=0)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=3, max_length=255)
    price: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)

class ProductRead(ProductBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class ProductResponse(BaseModel):
    message: str
    product: ProductRead

class ProductListResponse(BaseModel):
    message: str
    products: list[ProductRead]

class ProductDeleteResponse(BaseModel):
    message: str