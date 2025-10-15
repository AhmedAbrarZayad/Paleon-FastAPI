# app/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    OPENAI_API_KEY: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
