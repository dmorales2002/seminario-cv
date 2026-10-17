from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_SECRET_KEY_LENGTH = 32

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "MVP Preselección de Candidatos"
    SECRET_KEY: str  # obligatoria: sin valor predeterminado
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 horas
    ALGORITHM: str = "HS256"
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5433/mvp_db"
    UPLOAD_DIR: Path = Path(__file__).resolve().parents[2] / "uploads"
    MAX_CV_SIZE_MB: int = 5
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    CORS_ORIGIN_REGEX: str | None = None  # e.g. r"https://.*\.vercel\.app"
    RECRUITER_INVITE_CODE: str | None = None  # sin valor, el registro de reclutadores queda deshabilitado
    ANALYSIS_TIME_BUDGET_SECONDS: float = 40.0  # tope por solicitud de análisis (la función dura 60 s)
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini-2024-07-18"
    OPENAI_TIMEOUT_SECONDS: float = 60.0
    OPENAI_MAX_RETRIES: int = 2
    LLM_MAX_DOCUMENT_CHARS: int = 60_000

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < MIN_SECRET_KEY_LENGTH or value.upper().startswith(("SUPER_SECRET", "REPLACE-WITH")):
            raise ValueError(
                f"SECRET_KEY debe tener al menos {MIN_SECRET_KEY_LENGTH} caracteres y no puede ser un valor de ejemplo."
            )
        return value


settings = Settings()
