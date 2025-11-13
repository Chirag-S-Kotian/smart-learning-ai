from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from app.schemas.tracking import (
    VideoWatchingRequest, VideoWatchingUpdate, VideoWatchingResponse,
    VideoWatchingStatsResponse, CourseProgressInit, CourseProgressUpdate,
    CourseProgressResponse, UserAllCoursesProgressResponse, ModuleProgressResponse,
    VideoWatchStartResponse
)
from app.dependencies import get_current_user
from app.services.course_tracking_service import course_tracking_service
from app.core.supabase_client import supabase_client

router = APIRouter()


# ============ Video Watching Endpoints ============

@router.post("/videos/watch/start", response_model=VideoWatchStartResponse, status_code=status.HTTP_201_CREATED)
async def start_video_watch(
    watch_request: VideoWatchingRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Start tracking a video watch session
    Returns a session_id for tracking subsequent updates
    """
    try:
        result = course_tracking_service.start_video_watch(
            user_id=current_user["id"],
            video_id=watch_request.video_id,
            course_id=watch_request.course_id,
            module_id=watch_request.module_id,
            total_video_duration=watch_request.total_video_duration
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return VideoWatchStartResponse(
            success=True,
            session_id=result["session_id"],
            watch_id=result["watch_id"],
            message="Video watch session started"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/videos/watch/{watch_id}", response_model=VideoWatchingResponse)
async def update_video_watch(
    watch_id: str,
    update: VideoWatchingUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update video watch progress (call periodically as user watches)
    """
    try:
        # Verify ownership
        watch = supabase_client.table("video_watching").select("user_id").eq(
            "id", watch_id
        ).single().execute()
        
        if not watch.data:
            raise HTTPException(status_code=404, detail="Watch record not found")
        
        if watch.data["user_id"] != current_user["id"] and current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")
        
        result = course_tracking_service.update_video_watch(
            watch_id=watch_id,
            duration_watched=update.duration_watched,
            watch_percentage=update.watch_percentage,
            playback_speed=update.playback_speed
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return VideoWatchingResponse(**result["watch_data"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/videos/watch/{watch_id}/complete", response_model=VideoWatchingResponse)
async def complete_video_watch(
    watch_id: str,
    update: VideoWatchingUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark a video watch as completed
    Student must watch >= 80% to mark as complete
    """
    try:
        # Verify ownership
        watch = supabase_client.table("video_watching").select("user_id").eq(
            "id", watch_id
        ).single().execute()
        
        if not watch.data:
            raise HTTPException(status_code=404, detail="Watch record not found")
        
        if watch.data["user_id"] != current_user["id"] and current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")
        
        result = course_tracking_service.complete_video_watch(
            watch_id=watch_id,
            duration_watched=update.duration_watched,
            watch_percentage=update.watch_percentage
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        if result.get("is_completed"):
            # Update course progress
            watch_data = watch.data  # Get original watch data
            course_tracking_service.update_course_progress(
                user_id=current_user["id"],
                course_id=watch_data["course_id"],
                videos_watched=1
            )
        
        return VideoWatchingResponse(**result["watch_data"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/videos/watch/stats/{course_id}", response_model=VideoWatchingStatsResponse)
async def get_video_watching_stats(
    course_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get video watching statistics for user in a course
    """
    try:
        result = course_tracking_service.get_user_video_watch_stats(
            user_id=current_user["id"],
            course_id=course_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return VideoWatchingStatsResponse(
            total_videos_started=result["total_videos_started"],
            total_videos_completed=result["total_videos_completed"],
            total_duration_watched=result["total_duration_watched"],
            average_watch_percentage=result["average_watch_percentage"],
            videos=[VideoWatchingResponse(**v) for v in result["videos"]]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Course Progress Endpoints ============

@router.post("/courses/{course_id}/progress/init", response_model=CourseProgressResponse, status_code=status.HTTP_201_CREATED)
async def initialize_course_progress(
    course_id: str,
    enrollment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Initialize course progress tracking for a student
    Call this when student enrolls in a course
    """
    try:
        result = course_tracking_service.init_course_progress(
            user_id=current_user["id"],
            course_id=course_id,
            enrollment_id=enrollment_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return CourseProgressResponse(**result["progress_data"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/courses/{course_id}/progress", response_model=CourseProgressResponse)
async def get_course_progress(
    course_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get course progress for current user
    """
    try:
        result = course_tracking_service.get_course_progress(
            user_id=current_user["id"],
            course_id=course_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return CourseProgressResponse(**result["progress_data"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/courses/{course_id}/progress", response_model=CourseProgressResponse)
async def update_course_progress(
    course_id: str,
    update: CourseProgressUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update course progress
    """
    try:
        result = course_tracking_service.update_course_progress(
            user_id=current_user["id"],
            course_id=course_id,
            videos_watched=update.videos_watched,
            assessments_passed=update.assessments_passed,
            time_spent=update.time_spent,
            current_module_id=update.current_module_id,
            current_video_id=update.current_video_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return CourseProgressResponse(**result["progress_data"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/courses/progress", response_model=UserAllCoursesProgressResponse)
async def get_all_courses_progress(
    current_user: dict = Depends(get_current_user)
):
    """
    Get progress for all courses user is enrolled in
    """
    try:
        result = course_tracking_service.get_user_all_courses_progress(
            user_id=current_user["id"]
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return UserAllCoursesProgressResponse(
            total_courses=result["total_courses"],
            average_completion=result["average_completion"],
            courses_progress=[CourseProgressResponse(**c) for c in result["courses_progress"]]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Module Progress Endpoints ============

@router.post("/modules/{module_id}/progress/init", response_model=ModuleProgressResponse, status_code=status.HTTP_201_CREATED)
async def initialize_module_progress(
    module_id: str,
    course_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Initialize module progress tracking
    """
    try:
        result = course_tracking_service.init_module_progress(
            user_id=current_user["id"],
            module_id=module_id,
            course_id=course_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return ModuleProgressResponse(**result["progress_data"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modules/{module_id}/progress", response_model=ModuleProgressResponse)
async def get_module_progress(
    module_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get module progress for current user
    """
    try:
        result = course_tracking_service.get_module_progress(
            user_id=current_user["id"],
            module_id=module_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return ModuleProgressResponse(**result["progress_data"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
