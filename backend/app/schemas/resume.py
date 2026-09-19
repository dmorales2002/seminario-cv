from pydantic import BaseModel
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
