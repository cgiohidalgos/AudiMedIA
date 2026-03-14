from pydantic_settings import BaseSettings
from typing import List
import json
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_DB = (BACKEND_DIR / "audiomedia.db").as_posix()


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AudiMedIA API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # CORS
    ALLOWED_ORIGINS: str | List[str] = '["http://localhost:5173","http://localhost:3000","http://localhost:8080","http://localhost:8081","http://localhost:8082","http://localhost:4173"]'
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS from JSON string or return as list"""
        if isinstance(self.ALLOWED_ORIGINS, str):
            try:
                return json.loads(self.ALLOWED_ORIGINS)
            except json.JSONDecodeError:
                return [self.ALLOWED_ORIGINS]
        return self.ALLOWED_ORIGINS

    # Database (SQLite por defecto, fija al backend para no depender del cwd)
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DEFAULT_SQLITE_DB}"

    # Security / JWT
    SECRET_KEY: str = "changeme-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # LLM
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_MAX_TOKENS: int = 1200

    # Si el texto es muy grande, se crea un resumen más pequeño antes de extraer variables.
    # Esto reduce el uso de tokens al procesar PDFs muy largos.
    LLM_USE_SUMMARIZATION: bool = True
    LLM_SUMMARIZE_THRESHOLD_CHARS: int = 100_000
    LLM_SUMMARIZE_CHUNK_SIZE: int = 12_000
    LLM_SUMMARIZE_MAX_TOKENS: int = 800

    # Almacenamiento de PDFs
    UPLOAD_DIR: str = "/tmp/audiomedia/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignorar variables extra como VITE_*


settings = Settings()
