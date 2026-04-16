from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate, ProductListResponse
from app.services.product import get_product, get_products, create_product, update_product, delete_product

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/", response_model=ProductListResponse)
def read_products(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
) -> ProductListResponse:
    products = get_products(db, skip, limit)
    return ProductListResponse(message="Products fetched successfully", products=products)

@router.get("/{product_id}", response_model=ProductRead)
def read_product(
    product_id: int,
    db: Session = Depends(get_db),
) -> ProductRead:
    product = get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
) -> ProductRead:
    return create_product(db, payload)

@router.put("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
) -> ProductRead:
    return update_product(db, product_id, payload)

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
) -> Response:
    delete_product(db, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT) 