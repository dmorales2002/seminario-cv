from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from app.models.user import UserRole

class UserBase(BaseModel):
    full_name: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    role: UserRole

class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None

class UserOut(UserBase):
    id: UUID
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True
