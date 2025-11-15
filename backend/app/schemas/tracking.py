from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============ Video Watching Schemas ============

class VideoWatchingRequest(BaseModel):
    """Schema for starting video watch"""
    video_id: str
    course_id: str
    module_id: str
    total_video_duration: Optional[int] = None


class VideoWatchingUpdate(BaseModel):
    """Schema for updating video watch progress"""
    duration_watched: int = Field(..., description="Seconds watched")
    watch_percentage: float = Field(..., ge=0, le=100, description="Percentage watched")
    playback_speed: float = Field(default=1.0, description="Playback speed")


class VideoWatchingResponse(BaseModel):
    """Schema for video watching response"""
    id: str
    user_id: str
    video_id: str
    course_id: str
    module_id: str
    watch_start_time: datetime
    watch_end_time: Optional[datetime] = None
    duration_watched: int
    total_video_duration: Optional[int] = None
    watch_percentage: float
    playback_speed: float
    is_completed: bool
    completion_date: Optional[datetime] = None
    view_count: int
    session_id: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class VideoWatchingStatsResponse(BaseModel):
    """Schema for video watching statistics"""
    total_videos_started: int
    total_videos_completed: int
    total_duration_watched: int
    average_watch_percentage: float
    videos: List[VideoWatchingResponse]


# ============ Course Progress Schemas ============

class CourseProgressInit(BaseModel):
    """Schema for initializing course progress"""
    course_id: str
    enrollment_id: str


class CourseProgressUpdate(BaseModel):
    """Schema for updating course progress"""
    videos_watched: Optional[int] = None
    assessments_passed: Optional[int] = None
    time_spent: Optional[int] = None  # Additional time in seconds
    current_module_id: Optional[str] = None
    current_video_id: Optional[str] = None


class CourseProgressResponse(BaseModel):
    """Schema for course progress response"""
    id: str
    user_id: str
    course_id: str
    enrollment_id: str
    total_modules: int
    completed_modules: int
    total_videos: int
    videos_watched: int
    total_assessments: int
    assessments_passed: int
    overall_completion_percentage: float
    course_status: str  # in_progress, completed, dropped
    time_spent: int  # total time in seconds
    last_accessed: datetime
    completion_date: Optional[datetime] = None
    estimated_completion_date: Optional[datetime] = None
    current_module_id: Optional[str] = None
    current_video_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserAllCoursesProgressResponse(BaseModel):
    """Schema for all courses progress of a user"""
    total_courses: int
    average_completion: float
    courses_progress: List[CourseProgressResponse]


# ============ Module Progress Schemas ============

class ModuleProgressResponse(BaseModel):
    """Schema for module progress response"""
    id: str
    user_id: str
    module_id: str
    course_id: str
    total_content_items: int
    completed_content_items: int
    total_videos: int
    videos_watched: int
    total_assessments: int
    assessments_passed: int
    module_completion_percentage: float
    time_spent: int  # total time in seconds
    last_accessed: datetime
    completion_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============ Generic Response Schemas ============

class TrackingSuccessResponse(BaseModel):
    """Generic success response for tracking operations"""
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class VideoWatchStartResponse(BaseModel):
    """Response for starting video watch"""
    success: bool
    session_id: str
    watch_id: str
    message: Optional[str] = None
