from fastapi import FastAPI

from app.routes.user import router as user_router


app = FastAPI(title="FastAPI Project")
app.include_router(user_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello World"}
