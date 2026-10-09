from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime


class ResumeOut(BaseModel):
    id: UUID
    candidate_id: UUID
    file_path: str
    file_type: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ── Harvard CV ────────────────────────────────────────────────────────────────

class HarvardSection(BaseModel):
    """Una sección del CV Harvard (ej. Educación, Experiencia)."""
    model_config = ConfigDict(extra="forbid")

    heading: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=4000)


class HarvardCV(BaseModel):
    """Estructura completa de un CV en formato Harvard."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    contact: str = Field(max_length=400, description="Email, teléfono y/o dirección separados por ' | '")
    sections: list[HarvardSection] = Field(min_length=1, max_length=15)
