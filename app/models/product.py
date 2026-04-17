import uuid
from sqlalchemy import Enum, String, ForeignKey, Float, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.db.base import Base
from sqlalchemy.orm import Mapped, mapped_column


class Product(Base):
    __tablename__ = "product"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("category.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False)