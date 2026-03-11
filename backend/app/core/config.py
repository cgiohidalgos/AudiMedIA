from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AudiMedIA API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Database (SQLite por defecto)
    DATABASE_URL: str = "sqlite+aiosqlite:///./audiomedia.db"

    # Security / JWT
    SECRET_KEY: str = "changeme-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # LLM
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"

    # Almacenamiento de PDFs
    UPLOAD_DIR: str = "/tmp/audiomedia/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
