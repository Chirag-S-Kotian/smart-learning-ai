from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ContentCreate(BaseModel):
    course_id: str
    title: str


class ContentRead(BaseModel):
    id: str
    course_id: str
    title: str


# ============ Course Video Schemas ============

class CourseVideoUpload(BaseModel):
    """Schema for video upload metadata"""
    course_id: str
    module_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    order: int = 0


class CourseVideoResponse(BaseModel):
    """Schema for video response"""
    video_id: str
    course_id: str
    module_id: str
    original_filename: str
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str
    video_url: str
    status: str = "uploaded"  # uploaded, processing, ready, error
    duration: Optional[int] = None  # Duration in seconds
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    uploaded_by: str
    uploaded_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class VideoUploadResponse(BaseModel):
    """Schema for upload endpoint response"""
    success: bool
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    file_size: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None
    video_data: Optional[CourseVideoResponse] = None


class ModuleVideosResponse(BaseModel):
    """Schema for listing module videos"""
    videos: List[CourseVideoResponse]
    count: int
    total_size: Optional[int] = None


class VideoMetadataUpdate(BaseModel):
    """Schema for updating video metadata"""
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    thumbnail_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


