import hashlib
import hmac
import os

from sqlalchemy.orm import Session
from app.models import Product
from app.schemas.product import ProductCreate, ProductUpdate


def get_product(db: Session, product_id: int) -> Product | None:
    return db.query(Product).filter(Product.id == product_id).first()

def get_products(db: Session, skip: int = 0, limit: int = 10) -> list[Product]:
    return db.query(Product).offset(skip).limit(limit).all()

def create_product(db: Session, product: ProductCreate) -> Product:
    db_product = Product(
        name=product.name,
        description=product.description,
        price=product.price,
        stock=product.stock,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, product_id: int, product: ProductUpdate) -> Product | None:
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    db_product.name = product.name
    db_product.description = product.description
    db_product.price = product.price
    db_product.stock = product.stock
    db.commit()
    db.refresh(db_product)
    return db_product

def delete_product(db: Session, product_id: int) -> Product | None:
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    db.delete(db_product)
    db.commit()
    return db_product  
