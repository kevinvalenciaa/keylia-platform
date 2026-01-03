"""Application configuration."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    SECURITY: Default values are set for production safety.
    - DEBUG defaults to False to prevent stack trace exposure
    - Required secrets have no defaults to force explicit configuration
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    VERSION: str = "0.1.0"
    # SECURITY: DEBUG must default to False for production safety
    # Stack traces and internal paths are exposed when DEBUG=True
    DEBUG: bool = False
    SECRET_KEY: str  # Required - must be set in environment
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://keylia.io",
    ]
    
    # Database (Supabase or PostgreSQL)
    # Supabase format: postgresql+asyncpg://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
    # Local format: postgresql+asyncpg://postgres:PASSWORD@localhost:5432/keylia
    DATABASE_URL: str  # Required - must be set in environment
    
    # Supabase (optional - if using Supabase)
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    NEXT_PUBLIC_SUPABASE_URL: str = ""
    NEXT_PUBLIC_SUPABASE_ANON_KEY: str = ""
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    JWT_SECRET_KEY: str  # Required - must be set in environment
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "keylia-media"
    S3_BUCKET_URL: str = ""
    
    # OpenAI (optional)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4-turbo"
    OPENAI_VISION_MODEL: str = "gpt-4-vision-preview"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    
    # ElevenLabs (TTS)
    ELEVENLABS_API_KEY: str = ""
    
    # HeyGen (Avatar)
    HEYGEN_API_KEY: str = ""
    
    # fal.ai (Video Generation)
    FAL_KEY: str = ""
    FAL_VIDEO_MODEL: str = "fal-ai/kling-video/v1/pro/image-to-video"
    FAL_IMAGE_TO_VIDEO_MODEL: str = "fal-ai/kling-video/v1/pro/image-to-video"
    FAL_KLING_MODEL: str = "fal-ai/kling-video/v1/pro/image-to-video"
    
    # Frontend URL (for redirects)
    FRONTEND_URL: str = "http://localhost:3000"

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_PROFESSIONAL: str = ""
    STRIPE_PRICE_TEAM: str = ""
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

