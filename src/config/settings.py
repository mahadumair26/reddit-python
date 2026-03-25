"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    APP_NAME: str = "Reddit Scraper Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = False

    API_PREFIX: str = "/api/v1"
    API_KEY: Optional[str] = None
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    REDDIT_BASE_URL: str = "https://old.reddit.com"
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0

    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_PERIOD: int = 60
    MIN_REQUEST_DELAY: float = 1.0
    MAX_REQUEST_DELAY: float = 3.0

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    CACHE_TTL_POSTS: int = 3600
    CACHE_TTL_SUBREDDIT: int = 86400
    CACHE_TTL_USER: int = 3600

    DATABASE_URL: Optional[str] = None
    DB_ECHO: bool = False

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/scraper.log"
    LOG_ROTATION: str = "500 MB"
    LOG_RETENTION: str = "30 days"

    USE_PROXY: bool = False
    PROXY_URL: Optional[str] = None
    PROXY_ROTATION: bool = False

    USE_BROWSER: bool = False
    HEADLESS: bool = True

    MAX_POSTS_PER_REQUEST: int = 100
    MAX_COMMENTS_PER_POST: int = 500

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Get memoized settings object."""
    return Settings()


settings = get_settings()
