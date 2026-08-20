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

    # Cloudflare R2 configuration (S3-compatible)
    R2_ENDPOINT_URL: str 
    R2_ACCESS_KEY_ID: str
    R2_SECRET_ACCESS_KEY: str 
    R2_BUCKET_NAME: str = "nephos"
    
    REDIS_URL: str = "redis://localhost:6379/0"

    # Load from .env file
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()