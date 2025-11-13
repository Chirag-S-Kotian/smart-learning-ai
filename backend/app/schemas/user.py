from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.schemas.auth import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    bio: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase):
    id: str
    avatar_url: Optional[str] = None
    is_active: bool
    email_verified: bool
    phone_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    email_verified: bool
    phone_verified: bool
    created_at: datetime
    
    # Statistics (for students)
    enrolled_courses: Optional[int] = 0
    completed_courses: Optional[int] = 0
    total_assessments_taken: Optional[int] = 0
    average_score: Optional[float] = 0.0
    
    class Config:
        from_attributes = True