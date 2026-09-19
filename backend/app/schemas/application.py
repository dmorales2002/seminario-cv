from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Any
from app.models.application import ApplicationStatus

class ApplicationOut(BaseModel):
    id: UUID
    vacancy_id: UUID
    candidate_id: UUID
    resume_id: UUID
    ai_score: int | None = None
    ai_evidence: Any | None = None
    analysis_status: str
    analysis_error: str | None = None
    analyzed_at: datetime | None = None
    analyzer_version: str | None = None
    status: ApplicationStatus
    applied_at: datetime

    class Config:
        from_attributes = True

class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus

class ApplicationWithCandidateOut(ApplicationOut):
    """Extended schema used in the recruiter's panel, includes candidate name."""
    candidate_name: str | None = None
    candidate_email: str | None = None
