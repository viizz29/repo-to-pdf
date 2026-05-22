from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql://user:password@db:5432/app"
    APP_ENV: str = "development"
    CORS_ALLOW_ORIGINS: list[str] = ["*"]
    SECRET_KEY: str = "supersecret"
    ALGORITHM: str = "HS256"
    HASHIDS_SALT: str = "change-me"
    STORAGE_DIR: str = "images"
    FACE_MATCH_TOLERANCE: float = 0.48
    AZURE_OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_DEPLOYMENT: str | None = None
    AZURE_OPENAI_API_VERSION: str = "2025-01-01-preview"

settings = Settings()
