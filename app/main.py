from fastapi import FastAPI
import logging

from app.db.base import Base
from app.db.session import SessionLocal, engine, wait_for_db
from app.core.logging import setup_logging
from app.routes.user import router as user_router
from app.routes.category import router as category_router
from app.routes.product import router as product_router
from app.routes.chat import router as chat_router
from app.routes.ai import router as ai_router
from app.core.config import settings
from app.services.chat import chat_memory_service
from app.services.chat_cache import chat_cache_service

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
app.include_router(user_router)
app.include_router(category_router)
app.include_router(product_router)
app.include_router(chat_router)
app.include_router(ai_router)


@app.on_event("startup")
def on_startup() -> None:
    logger.info("startup.begin app=%s debug=%s", settings.app_name, settings.debug)
    logger.info("startup.db_wait.begin")
    wait_for_db()
    logger.info("startup.db_wait.success")
    logger.info("startup.db_migrate.begin")
    Base.metadata.create_all(bind=engine)
    logger.info("startup.db_migrate.success")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello World"}


@app.on_event("shutdown")
def on_shutdown() -> None:
    pending_before = chat_cache_service.pending_count()
    if pending_before <= 0:
        return

    logger.info("shutdown.chat_cache_flush.begin pending=%d", pending_before)
    db = SessionLocal()
    flushed_total = 0
    try:
        while True:
            pending = chat_cache_service.pop_pending_batch(settings.chat_cache_flush_batch_size)
            if not pending:
                break

            rows = [(item.session_id, item.role, item.message) for item in pending]
            flushed_total += chat_memory_service.add_messages_bulk(db, rows)
    finally:
        db.close()

    logger.info("shutdown.chat_cache_flush.success flushed=%d", flushed_total)