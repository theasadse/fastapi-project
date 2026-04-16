
from sqlalchemy import Enum, String, ForeignKey, Float, Integer
from app.db.base import Base
from sqlalchemy.orm import Mapped, mapped_column

class Category(Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user1.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)