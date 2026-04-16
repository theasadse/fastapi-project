
from sqlalchemy import Enum, String, ForeignKey, Float, Integer
from app.db.base import Base
from sqlalchemy.orm import Mapped, mapped_column


class Product(Base):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user1.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False)