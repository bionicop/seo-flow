"""
Application settings using pydantic-settings.

All configuration is loaded from environment variables or .env file.
Provides type validation and sensible defaults.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Data Sources ===
    serper_api_key: str = Field(
        default="",
        description="Serper.dev API key for SERP data",
    )
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key for AI insights",
    )
    gsc_credentials_path: Path | None = Field(
        default=None,
        description="Path to Google Search Console service account JSON",
    )

    # === Defaults ===
    default_data_source: Literal["serper", "duckduckgo", "gsc"] = Field(
        default="serper",
        description="Default data collection source",
    )
    default_result_count: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of results to fetch",
    )
    default_country: str = Field(
        default="us",
        description="Country code for search localization",
    )
    default_language: str = Field(
        default="en",
        description="Language code for search",
    )

    # === Output ===
    output_format: Literal["markdown", "html", "both"] = Field(
        default="both",
        description="Report output format",
    )
    reports_dir: Path = Field(
        default=Path("./reports"),
        description="Directory for generated reports",
    )
    data_dir: Path = Field(
        default=Path("./data"),
        description="Directory for data storage",
    )

    # === Rate Limiting ===
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for API calls",
    )
    retry_delay_seconds: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Delay between retries in seconds",
    )
    request_timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=120,
        description="HTTP request timeout",
    )

    # === n8n ===
    n8n_webhook_url: str | None = Field(
        default=None,
        description="n8n webhook URL for triggering workflows",
    )

    @field_validator("gsc_credentials_path", mode="before")
    @classmethod
    def validate_gsc_path(cls, v: str | Path | None) -> Path | None:
        """Convert string path to Path object if provided."""
        if v is None or v == "":
            return None
        path = Path(v)
        return path if path.exists() else None

    def has_serper_key(self) -> bool:
        """Check if Serper API key is configured."""
        return bool(self.serper_api_key)

    def has_gemini_key(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(self.gemini_api_key)

    def has_gsc_credentials(self) -> bool:
        """Check if GSC credentials are configured and valid."""
        return self.gsc_credentials_path is not None


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings: Application configuration instance.

    Example:
        >>> settings = get_settings()
        >>> print(settings.default_data_source)
        'serper'
    """
    return Settings()
