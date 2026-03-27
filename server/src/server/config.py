from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 200
    archive_retention_days: int = 30
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_prefix": "APR_"}
