from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class AppSettings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    OPENAI_API_KEY: Optional[str] = None

    LLM_PROVIDER: str = "openai"
    LLM_MODEL_NAME: Optional[str] = None

    WGER_API_URL: str = "https://localhost/api/v2"
    WGER_API_KEY: str = "invalid-api-key"
    WGER_LANGUAGE_ID: int = 2 # English

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore' # Ignore extra fields from .env if any
    )

settings = AppSettings()
