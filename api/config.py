"""
API Configuration - Environment-based settings
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App settings
    app_name: str = "SEC-Tracker API"
    app_version: str = "2.0.0"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql+asyncpg://sec_tracker:sec_tracker@localhost:5432/sec_tracker"
    database_echo: bool = False
    db_pool_size: int = 20
    db_max_overflow: int = 30
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600  # 1 hour default
    redis_max_connections: int = 200
    
    # JWT Authentication
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION_32_CHARS_MIN"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # SEC API
    sec_user_agent: Optional[str] = None
    sec_rate_limit: float = 10.0  # requests per second
    
    # OpenRouter (AI Analysis)
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "deepseek/deepseek-chat-v3.1:free"

    # Background jobs (Celery)
    celery_enabled: bool = False
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None
    
    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Reverse proxy / client IP handling
    # Comma-separated list of trusted proxy IPs/CIDRs (e.g., "172.16.0.0/12,10.0.0.0/8")
    trusted_proxies: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
