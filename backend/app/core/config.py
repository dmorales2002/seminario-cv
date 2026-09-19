from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "MVP Preselección de Candidatos"
    SECRET_KEY: str = "SUPER_SECRET_KEY_FOR_MVP_2026_REPLACE_IN_PRODUCTION"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5433/mvp_db"
    UPLOAD_DIR: Path = Path(__file__).resolve().parents[2] / "uploads"
    MAX_CV_SIZE_MB: int = 5
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini-2024-07-18"
    OPENAI_TIMEOUT_SECONDS: float = 60.0
    OPENAI_MAX_RETRIES: int = 2
    LLM_MAX_DOCUMENT_CHARS: int = 60_000

settings = Settings()
