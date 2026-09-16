from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "SimpleMagics"
    SECRET_KEY: str = "your-super-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/career_compass"

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://your-production-domain.com"
    ]

    ANTHROPIC_API_KEY: str = ""  # Optional: for server-side AI features

    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"

settings = Settings()
