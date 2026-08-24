"""ECDAT API Configuration using pydantic-settings."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API Server Configuration
    API_TITLE: str = "ECDAT API"
    API_VERSION: str = "1.0.0"
    API_KEY: str = "ecdat-secret-key-2026"
    DEBUG: bool = False

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./ecdat.db"
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None

    # LLM API Keys & Configurations
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_AI_STUDIO_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"


    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    GROK_API_KEY: Optional[str] = None
    XAI_API_KEY: Optional[str] = None
    GROK_MODEL: str = "grok-beta"
    GROK_BASE_URL: str = "https://api.x.ai/v1"

    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    NVIDIA_BUILD_API_KEY: Optional[str] = None
    NVIDIA_MODEL: str = "meta/llama-3.1-8b-instruct"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "llama3"

    # CORS & Network Configuration
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Scanner & Execution Settings
    SCAN_TIMEOUT_SECONDS: int = 120
    LLM_TIMEOUT_SECONDS: float = 6.0
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 500


settings = Settings()


