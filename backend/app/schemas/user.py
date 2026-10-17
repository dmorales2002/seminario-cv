from pydantic import BaseModel, EmailStr, Field, field_validator
from uuid import UUID
from datetime import datetime
from app.models.user import UserRole

class UserBase(BaseModel):
    full_name: str
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=72)
    role: UserRole
    invite_code: str | None = None  # obligatorio solo para el rol de reclutador

    @field_validator("password")
    @classmethod
    def password_needs_letter_and_digit(cls, value: str) -> str:
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("La contraseña debe incluir al menos una letra y un número.")
        return value

class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None

class UserOut(UserBase):
    id: UUID
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True
