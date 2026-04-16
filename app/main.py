from fastapi import FastAPI

from app.db.base import Base
from app.db.session import engine
from app.models import user as user_model
from app.routes.user import router as user_router
from app.core.config import settings


app = FastAPI(title=settings.app_name)
app.include_router(user_router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello World"}
