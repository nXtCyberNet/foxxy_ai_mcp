"""
Configuration settings for ArmorIQ Validation Service.
"""
from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: str = Field(default="development", description="Environment (development/production)")
    
    # Service Info
    service_name: str = Field(default="ArmorIQ Validation Service", description="Service name")
    service_version: str = Field(default="1.0.0", description="Service version")
    port: int = Field(default=8001, description="Service port")

    # ArmorIQ Configuration
    armoriq_api_key: Optional[SecretStr] = Field(default=None, description="ArmorIQ API key")
    armoriq_proxy_url: str = Field(
        default="https://customer-proxy.armoriq.ai",
        description="ArmorIQ proxy endpoint"
    )
    armoriq_backend_url: str = Field(
        default="https://customer-api.armoriq.ai", 
        description="ArmorIQ backend endpoint"
    )

    # Validation Settings
    validation_threshold: float = Field(
        default=75.0, 
        ge=0.0, 
        le=100.0,
        description="Default credibility threshold for pass/fail (0-100)"
    )
    max_tool_calls: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of tool calls to process"
    )
    execution_timeout: int = Field(
        default=60,
        ge=5,
        le=300,
        description="Execution timeout in seconds"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json/text)")

    # Optional Database (for audit logging)
    database_url: Optional[str] = Field(default=None, description="Database URL for audit logging")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"
    
    @property
    def has_armoriq_config(self) -> bool:
        """Check if ArmorIQ is properly configured."""
        return self.armoriq_api_key is not None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()


# Constants
class ValidationConstants:
    """Validation-specific constants."""
    
    # Credibility weights
    PLAN_INTEGRITY_WEIGHT = 0.2
    EXECUTION_SUCCESS_WEIGHT = 0.4
    RESPONSE_CONSISTENCY_WEIGHT = 0.3
    SECURITY_COMPLIANCE_WEIGHT = 0.1
    
    # Score thresholds
    MIN_CREDIBILITY_SCORE = 0.0
    MAX_CREDIBILITY_SCORE = 100.0
    
    # API limits
    MAX_CONTENT_LENGTH = 100000  # 100KB
    MAX_TOOL_NAME_LENGTH = 200
    
    # Timeouts
    ARMORIQ_REQUEST_TIMEOUT = 30
    TOOL_EXECUTION_TIMEOUT = 60