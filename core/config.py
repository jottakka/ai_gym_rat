from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class AppSettings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    OPENAI_API_KEY: Optional[str] = None

    LLM_PROVIDER: str = "openai" # Default provider
    LLM_MODEL_NAME: Optional[str] = None # e.g., "gpt-4o-mini" or "gemini-1.5-flash"

    WGER_API_URL: str = "https://wger.de/api/v2"
    WGER_LANGUAGE_ID: int = 2 # English

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore' # Ignore extra fields from .env if any
    )

settings = AppSettings()
