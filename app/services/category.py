import hashlib
import hmac
import os

from sqlalchemy.orm import Session
from app.models.category import Category


def get_category(db: Session, category_id: int) -> Category | None:
    return db.query(Category).filter(Category.id == category_id).first()

def get_categories(db: Session, skip: int = 0, limit: int = 10) -> list[Category]:
    return db.query(Category).offset(skip).limit(limit).all()

def create_category(db: Session, category: CategoryCreate) -> Category:
    db_category = Category(
        name=category.name,
        description=category.description,
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

def update_category(db: Session, category_id: int, category: CategoryUpdate) -> Category | None:
    db_category = get_category(db, category_id)
    if not db_category:
        return None
    db_category.name = category.name
    db_category.description = category.description
    db.commit()
    db.refresh(db_category)
    return db_category

def delete_category(db: Session, category_id: int) -> Category | None:
    db_category = get_category(db, category_id)
    if not db_category:
        return None
    db.delete(db_category)
    db.commit()
    return db_category  
