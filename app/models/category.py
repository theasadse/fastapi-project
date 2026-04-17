import uuid
from sqlalchemy import Enum, String, ForeignKey, Float, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.db.base import Base
from sqlalchemy.orm import Mapped, mapped_column

class Category(Base):
    __tablename__ = "category"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)