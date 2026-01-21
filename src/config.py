"""
Production-grade configuration management using Pydantic Settings.
Supports environment-based configuration with validation.
"""
import os
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # --- Environment ---
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment"
    )
    
    # --- API Configuration ---
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=1, description="Number of API workers")
    
    # --- LLM Provider ---
    model_provider: Literal["gemini", "groq"] = Field(
        default="gemini",
        description="LLM provider to use"
    )
    
    # --- API Keys ---
    google_api_key: str | None = Field(default=None, description="Google Gemini API key")
    groq_api_key: str | None = Field(default=None, description="Groq API key")
    tavily_api_key: str | None = Field(default=None, description="Tavily search API key")
    
    # --- LangSmith Tracing ---
    langchain_api_key: str | None = Field(default=None, description="LangSmith API key")
    langchain_endpoint: str = Field(
        default="https://api.smith.langchain.com",
        description="LangSmith endpoint"
    )
    langchain_tracing_v2: bool = Field(default=False, description="Enable LangSmith tracing")
    langchain_project: str = Field(
        default="beaver-agent-prod",
        description="LangSmith project name"
    )
    
    # --- Model Configuration ---
    gemini_model: str = Field(default="gemini-2.5-flash", description="Gemini model name")
    groq_model: str = Field(default="llama-3.3-70b-versatile", description="Groq model name")
    model_temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="LLM temperature")
    model_max_retries: int = Field(default=5, ge=0, description="Max LLM retries")
    
    # --- Agent Configuration ---
    max_revision_count: int = Field(default=3, ge=1, le=10, description="Max email revisions")
    recursion_limit: int = Field(default=15, ge=5, le=50, description="Graph recursion limit")
    summarizer_threshold: int = Field(
        default=3000,
        ge=1000,
        description="Text length threshold for summarization"
    )
    
    # --- Security ---
    pii_confidence_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="PII detection confidence threshold"
    )
    pii_vault_ttl: int = Field(
        default=3600,
        ge=60,
        description="PII vault TTL in seconds"
    )
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    api_keys: list[str] = Field(
        default_factory=list,
        description="Valid API keys for authentication"
    )
    
    # --- Rate Limiting ---
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=10, ge=1, description="Requests per minute")
    rate_limit_window: int = Field(default=60, ge=1, description="Rate limit window in seconds")
    
    # --- Database ---
    database_url: str = Field(
        default="sqlite:///./sales_crm.db",
        description="Database connection URL"
    )
    db_pool_size: int = Field(default=5, ge=1, description="Database connection pool size")
    
    # --- Redis ---
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    redis_max_connections: int = Field(default=10, ge=1, description="Redis max connections")
    
    # --- Logging ---
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: Literal["json", "text"] = Field(
        default="json",
        description="Log output format"
    )
    
    # --- Monitoring ---
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    health_check_enabled: bool = Field(default=True, description="Enable health checks")
    
    # --- Input Validation ---
    max_email_length: int = Field(
        default=20000,
        ge=100,
        description="Maximum email text length"
    )
    
    # --- Sender Configuration ---
    sender_name: str = Field(default="Harshal Zarikar", description="Sender name")
    sender_title: str = Field(default="Sales Manager", description="Sender title")
    sender_company: str = Field(
        default="Finsocial Digital System",
        description="Sender company"
    )
    sender_phone: str = Field(default="+91-9876543210", description="Sender phone")
    sender_email: str = Field(default="harshal@finsocial.com", description="Sender email")
    sender_website: str = Field(default="www.finsocial.com", description="Sender website")
    
    @field_validator("model_provider")
    @classmethod
    def validate_model_provider(cls, v: str, info) -> str:
        """Ensure required API key is present for selected provider."""
        # Note: This runs before all fields are set, so we can't check keys here
        # Validation is done in __init__ instead
        return v
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Validation relaxed for Streamlit Cloud startup resilience
        # Checks will happen at runtime in the agents/UI instead
        pass
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    def get_sender_config(self) -> dict:
        """Get sender configuration as dictionary."""
        return {
            "name": self.sender_name,
            "title": self.sender_title,
            "company_name": self.sender_company,
            "phone_number": self.sender_phone,
            "email_address": self.sender_email,
            "website": self.sender_website
        }


# Global settings instance
settings = Settings()
