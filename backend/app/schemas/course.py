from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_published: bool = False
    enrollment_open: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_published: Optional[bool] = None
    enrollment_open: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class CourseResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    instructor_id: str
    thumbnail_url: Optional[str] = None
    is_published: bool
    enrollment_open: bool
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    instructor_name: Optional[str] = None
    total_students: Optional[int] = None
    total_modules: Optional[int] = None
    total_content: Optional[int] = None

    class Config:
        from_attributes = True


class CourseDetailResponse(CourseResponse):
    modules: Optional[List['CourseModuleResponse']] = None


class CourseListResponse(BaseModel):
    courses: List[CourseResponse]
    total: int
    page: int
    page_size: int


class CourseModuleCreate(BaseModel):
    title: str
    description: Optional[str] = None
    order_index: int = 0


class CourseModuleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None


class CourseModuleResponse(BaseModel):
    id: str
    course_id: str
    title: str
    description: Optional[str] = None
    order_index: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Update forward references
CourseDetailResponse.model_rebuild()

