import uuid
from fastapi import APIRouter, Depends, Response, status, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate, CategoryListResponse
import app.services.category as category_service

router = APIRouter(prefix="/category", tags=["category"])

@router.get("/", response_model=CategoryListResponse)
def read_categories(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
) -> CategoryListResponse:
    categories = category_service.get_categories(db, skip, limit)
    return CategoryListResponse(
        message="Categories fetched successfully",
        categories=categories,
    )

@router.get("/{category_id}", response_model=CategoryRead)
def read_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> CategoryRead:
    category = category_service.get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
) -> CategoryRead:
    return category_service.create_category(db, payload)

@router.put("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
) -> CategoryRead:
    return category_service.update_category(db, category_id, payload)

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Response:
    category_service.delete_category(db, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT) 