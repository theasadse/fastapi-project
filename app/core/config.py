from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FastAPI Project"
    debug: bool = False
    log_level: str = "INFO"
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
    chat_semantic_top_k: int = 3
    chat_semantic_namespace_prefix: str = "chat-memory"
    redis_url: str = ""
    chat_cache_key_prefix: str = "chat-cache"
    chat_cache_session_message_limit: int = 20
    chat_cache_max_sessions: int = 2000
    chat_cache_session_ttl_seconds: int = 86400
    chat_cache_flush_batch_size: int = 100

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
