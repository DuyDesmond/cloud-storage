from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "Nephos"
    API_STR: str

    # Database Configuration (Neon Postgres)
    DATABASE_URL: str

    # JWT Security Configuration
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE: int
    REFRESH_TOKEN_EXPIRE: int

    # MinIO configuration for file storage
    MINIO_ENDPOINT: str | None = None
    MINIO_ACCESS_KEY: str | None = None
    MINIO_SECRET_KEY: str | None = None
    MINIO_SECURE: bool = False
    MINIO_BUCKET_NAME: str = "nephos"

    # Cloudflare R2 configuration (S3-compatible)
    R2_ENDPOINT_URL: str | None = None
    R2_ACCESS_KEY_ID: str | None = None
    R2_SECRET_ACCESS_KEY: str | None = None
    R2_BUCKET_NAME: str = "nephos"

    # Load from .env file
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()