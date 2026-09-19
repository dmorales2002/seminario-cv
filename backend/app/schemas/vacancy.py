from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from app.models.vacancy import VacancyStatus

class VacancyCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    requirements: str = Field(min_length=1)  # Base de conocimiento para el LLM

    @field_validator("title", "description", "requirements")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El campo no puede estar vacío.")
        return value

class VacancyUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    requirements: str | None = None
    status: VacancyStatus | None = None

    @field_validator("title", "description", "requirements")
    @classmethod
    def reject_blank_values(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("El campo no puede estar vacío.")
        return value

class VacancyOut(BaseModel):
    id: UUID
    recruiter_id: UUID
    title: str
    description: str
    requirements: str
    status: VacancyStatus
    created_at: datetime

    class Config:
        from_attributes = True

class VacancySummaryOut(VacancyOut):
    application_count: int = 0
    pending_count: int = 0
