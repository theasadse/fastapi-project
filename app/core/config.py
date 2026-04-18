from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FastAPI Project"
    debug: bool = False
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5437/fastapi_project"
    )
    postgres_db: str = "fastapi_project"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    pgadmin_default_email: str = "admin@example.com"
    pgadmin_default_password: str = "admin"
    db_startup_retries: int = 10
    db_startup_retry_delay: float = 2.0

    pinecone_api_key: str = ""
    pinecone_index_name: str = "fastapi-docs-local"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
