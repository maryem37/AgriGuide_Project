from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "AgriMent API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite+aiosqlite:///./agriment.db"

    JWT_SECRET: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    MISTRAL_API_KEY: str = ""
    MISTRAL_MODEL: str = "pixtral-12b-latest"
    MISTRAL_API_URL: str = "https://api.mistral.ai/v1/chat/completions"

    GEMMA_API_KEY: str = ""
    GEMMA_MODEL: str = "gemini-3.5-flash"
    GEMMA_API_URL: str = "https://generativelanguage.googleapis.com/v1beta/models"

    QWEN_API_KEY: str = ""
    QWEN_MODEL: str = "qwen-vl-max"
    QWEN_API_URL: str = "https://dashscope.aliyuncs.com/v1"

    VISION_PROVIDER: str = "gemma"

    FIREBASE_CREDENTIALS_PATH: str = "firebase_service_account.json"

    # TEST ONLY: when true, the farmer who triggers a region alert is also
    # notified (a Notification row is created and a push is sent to their
    # device). Set back to false (or remove from .env) for production so
    # senders don't receive their own alerts.
    ALERT_INCLUDE_SENDER: bool = True

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024

    ALLOWED_ORIGINS: list[str] = ["*"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
