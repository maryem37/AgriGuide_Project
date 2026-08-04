"""Configuration via variables d'environnement (alignée sur les autres agents)."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/agent_monitoring/app/config.py → repo root = parents[3]
_APP_DIR = Path(__file__).resolve().parent.parent  # backend/agent_monitoring/
_REPO_ROOT = _APP_DIR.parent.parent  # AgriGuide/


class Settings(BaseSettings):
    mistral_api_key: str = ""
    mistral_model: str = "mistral-medium-latest"
    open_meteo_base: str = "https://api.open-meteo.com/v1/forecast"

    # Racine du repo d'abord (MISTRAL_API_KEY partagée), puis .env local optionnel.
    model_config = SettingsConfigDict(
        env_file=(str(_REPO_ROOT / ".env"), str(_APP_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
