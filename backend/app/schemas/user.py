from pydantic import BaseModel, EmailStr
from datetime import datetime
from app.models.user import AppRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: AppRole = AppRole.auditor


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: AppRole | None = None
    is_active: bool | None = None


class UserRead(UserBase):
    id: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
