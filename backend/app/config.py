from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "LekhaJokha"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://lekhajokha:lekhajokha_dev@localhost:5432/lekhajokha"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OTP
    OTP_MOCK: bool = True
    OTP_FIXED_CODE: str = "123456"

    # CORS
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"

    # MinIO
    MINIO_ENDPOINT: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "lekhajokha"

    # Google Cloud Vision (OCR)
    GOOGLE_VISION_API_KEY: str = ""
    GOOGLE_VISION_ENABLED: bool = False  # False = mock mode for dev

    # Ingest email domain (for auto-generated client emails)
    INGEST_EMAIL_DOMAIN: str = "ingest.lekhajokha.local"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
