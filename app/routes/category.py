from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate, CategoryListResponse
from app.services.category import get_category, get_categories, create_category, update_category, delete_category

router = APIRouter(prefix="/category", tags=["category"])

@router.get("/", response_model=CategoryListResponse)
def read_categories(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
) -> CategoryListResponse:
    categories = get_categories(db, skip, limit)
    return CategoryListResponse(
        message="Categories fetched successfully",
        categories=categories,
    )

@router.get("/{category_id}", response_model=CategoryRead)
def read_category(
    category_id: int,
    db: Session = Depends(get_db),
) -> CategoryRead:
    category = get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
) -> CategoryRead:
    return create_category(db, payload)

@router.put("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
) -> CategoryRead:
    return update_category(db, category_id, payload)

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
) -> Response:
    delete_category(db, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT) 