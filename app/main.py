from fastapi import FastAPI

from app.db.base import Base
from app.db.session import engine, wait_for_db
from app.routes.user import router as user_router
from app.routes.category import router as category_router
from app.routes.product import router as product_router
from app.routes.chat import router as chat_router
from app.core.config import settings


app = FastAPI(title=settings.app_name)
app.include_router(user_router)
app.include_router(category_router)
app.include_router(product_router)
app.include_router(chat_router)


@app.on_event("startup")
def on_startup() -> None:
    wait_for_db()
    Base.metadata.create_all(bind=engine)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello World"}
