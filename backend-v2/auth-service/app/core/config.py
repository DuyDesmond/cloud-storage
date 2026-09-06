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
    
    STORAGE_QUOTA_BYTES: int

    # Cloudflare R2 configuration (S3-compatible) - Local Dev
    R2_ENDPOINT_URL: str | None = None
    R2_ACCESS_KEY_ID: str | None = None
    R2_SECRET_ACCESS_KEY: str | None = None
    R2_BUCKET_NAME: str | None = None

    # AWS S3 Configuration - Cloud Dev
    ENVIRONMENT: str = "local"
    BUCKET_ENDPOINT_URL: str | None = None
    BUCKET_NAME: str | None = None
    BUCKET_REGION_NAME: str = "ap-southeast-1"
    REDIS_URL: str = "redis://localhost:6379/0"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # Load from .env file
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()