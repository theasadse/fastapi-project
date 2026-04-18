from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.chat_memory import ChatMemory
from app.models.user_memory import UserMemory


class ChatMemoryService:
    def add_message(
        self,
        db: Session,
        session_id: str,
        role: str,
        message: str,
    ) -> ChatMemory:
        memory = ChatMemory(session_id=session_id, role=role, message=message)
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    def get_recent_messages(
        self,
        db: Session,
        session_id: str,
        limit: int = 12,
    ) -> list[ChatMemory]:
        query = (
            select(ChatMemory)
            .where(ChatMemory.session_id == session_id)
            .order_by(ChatMemory.created_at.desc(), ChatMemory.id.desc())
            .limit(limit)
        )
        messages = list(db.scalars(query).all())
        return list(reversed(messages))

    def get_all_messages(self, db: Session, session_id: str) -> list[ChatMemory]:
        query = (
            select(ChatMemory)
            .where(ChatMemory.session_id == session_id)
            .order_by(ChatMemory.created_at.asc(), ChatMemory.id.asc())
        )
        return list(db.scalars(query).all())

    def clear_session(self, db: Session, session_id: str) -> int:
        statement = delete(ChatMemory).where(ChatMemory.session_id == session_id)
        result = db.execute(statement)
        db.commit()
        return result.rowcount or 0

    def set_long_term_memory(
        self,
        db: Session,
        session_id: str,
        memory: str,
    ) -> UserMemory:
        existing = db.get(UserMemory, session_id)
        if existing is None:
            existing = UserMemory(session_id=session_id, memory=memory)
            db.add(existing)
        else:
            existing.memory = memory

        db.commit()
        db.refresh(existing)
        return existing

    def get_long_term_memory(self, db: Session, session_id: str) -> UserMemory | None:
        return db.get(UserMemory, session_id)

    def clear_long_term_memory(self, db: Session, session_id: str) -> bool:
        existing = db.get(UserMemory, session_id)
        if existing is None:
            return False

        db.delete(existing)
        db.commit()
        return True


chat_memory_service = ChatMemoryService()
