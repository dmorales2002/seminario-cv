import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, Column, Integer, Enum, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

class ApplicationStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("vacancy_id", "candidate_id", name="uq_application_vacancy_candidate"),
        CheckConstraint("ai_score IS NULL OR (ai_score >= 0 AND ai_score <= 100)", name="ck_application_ai_score"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vacancy_id = Column(UUID(as_uuid=True), ForeignKey("vacancies.id"), nullable=False)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False)
    
    ai_score = Column(Integer, nullable=True)  # 0 a 100
    ai_evidence = Column(JSONB, nullable=True)
    analysis_status = Column(String(20), default="PENDING", nullable=False)
    analysis_error = Column(Text, nullable=True)
    analyzed_at = Column(DateTime(timezone=True), nullable=True)
    analyzer_version = Column(String(100), nullable=True)
    
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.PENDING, nullable=False)
    applied_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    vacancy = relationship("Vacancy", backref="applications")
    candidate = relationship("User", backref="applications")
    resume = relationship("Resume", backref="applications")
