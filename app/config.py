from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings"""
    
    # ===== API INFO =====
    PROJECT_NAME: str = "Paleon Fossil Classification API"
    VERSION: str = "1.0.0"
    
    # ===== SECURITY =====
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production-!!!!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours (was 30 minutes)
    
    # ===== SUPABASE =====
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str  # For server-side operations
    
    # ===== REDIS =====
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 2
    
    # ===== CELERY =====
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    
    # ===== OPENAI =====
    OPENAI_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()