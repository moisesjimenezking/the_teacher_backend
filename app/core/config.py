import os
from pathlib import Path

from pydantic_settings import BaseSettings


# Base directory of the backend package (backend/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "Conversator"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    # Whisper
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"

    # LLM
    LLM_PROVIDER: str = "openrouter"
    LLM_MODEL: str = "anthropic/claude-sonnet-4"
    OPENROUTER_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
