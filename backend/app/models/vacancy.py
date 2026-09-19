import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Enum, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

class VacancyStatus(str, enum.Enum):
    OPEN = "OPEN"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"

class Vacancy(Base):
    __tablename__ = "vacancies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recruiter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=False)
    status = Column(Enum(VacancyStatus), default=VacancyStatus.OPEN, nullable=False)
    ai_criteria = Column(JSONB, nullable=True)
    criteria_updated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    recruiter = relationship("User", backref="vacancies")
