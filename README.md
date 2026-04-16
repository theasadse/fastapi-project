# FastAPI Project

FastAPI project with PostgreSQL, SQLAlchemy ORM, and pgAdmin.

## Run locally

1. Copy `.env.example` to `.env`.
2. Start infrastructure with `docker compose up -d`.
3. Install dependencies with `pip install -r requirements.txt`.
4. Run the app with `uvicorn main:app --reload`.

## Services

- API: `http://127.0.0.1:8000`
- pgAdmin: `http://127.0.0.1:5050`
- PostgreSQL: `localhost:5432`
