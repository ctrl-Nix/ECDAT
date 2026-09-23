"""ECDAT API Configuration using pydantic-settings."""

from pathlib import Path
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API Server Configuration
    API_TITLE: str = "ECDAT API"
    API_VERSION: str = "1.0.0"
    # Generic API-key authentication is transitional and deliberately fails
    # closed when absent. Browser bundles must never contain this value.
    API_KEY: Optional[str] = None
    DEBUG: bool = False

    # JWT / bearer-token authentication
    AUTH_JWT_SECRET: Optional[str] = Field(default=None)
    AUTH_JWT_TTL_MINUTES: int = Field(default=60, ge=1)
    AUTH_BOOTSTRAP_ADMIN_USERNAME: str = Field(default="admin", min_length=1)
    AUTH_BOOTSTRAP_ADMIN_PASSWORD: Optional[str] = None
    AUTH_JWT_STORE_METHOD: Literal["localStorage", "httpOnly_cookie"] = "localStorage"

    # Database Configuration
    # If POSTGRES_* are provided, DATABASE_URL is auto-constructed.
    # If DATABASE_URL is explicitly set in .env, it takes precedence.
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None
    POSTGRES_SSL_MODE: Literal["disable", "require", "verify-ca", "verify-full"] = "verify-full"
    POSTGRES_SSL_ROOT_CERT: Optional[Path] = None

    @model_validator(mode="after")
    def construct_database_url(self) -> "Settings":
        """Auto-construct DATABASE_URL from POSTGRES_* if not explicitly provided."""
        if self.DATABASE_URL is None:
            if all([self.POSTGRES_USER, self.POSTGRES_PASSWORD, self.POSTGRES_DB]):
                self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            else:
                self.DATABASE_URL = "sqlite:///./ecdat.db"
        return self

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
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    NVIDIA_BUILD_API_KEY: Optional[str] = None
    NVIDIA_MODEL: str = "mistralai/mistral-7b-instruct-v0.3"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "llama3"
    ALLOW_REMOTE_REMEDIATION: bool = False

    # CORS & Network Configuration
    # The deployed dashboard uses the same TLS gateway origin, so cross-origin
    # browser access is disabled by default. Supply an explicit JSON list only
    # for an approved separate frontend origin.
    CORS_ORIGINS: list[str] = Field(default_factory=list)

    # Report-sync agents are enrolled out of band. The JSON mapping has the
    # shape {"agent-id": "base64-encoded-ed25519-public-key"} and must be
    # supplied only to the online ingestion service, never the browser.
    REPORT_SYNC_AGENT_KEYS: dict[str, str] = Field(default_factory=dict)
    REPORT_SYNC_REQUIRE_MTLS: bool = True
    REPORT_SYNC_MTLS_HEADER: str = "X-ECDAT-mTLS-Verified"
    REPORT_SYNC_MAX_BUNDLE_BYTES: int = 1 * 1024 * 1024
    SCAN_WORKSPACE_ROOT: Optional[Path] = None
    ENABLE_LOCAL_SCAN_API: bool = False

    # Scanner & Execution Settings
    SCAN_TIMEOUT_SECONDS: int = 120
    LLM_TIMEOUT_SECONDS: float = 6.0
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 500


settings = Settings()


