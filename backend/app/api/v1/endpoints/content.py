from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from typing import List, Optional
from app.schemas.content import (
    CourseVideoUpload, CourseVideoResponse, VideoUploadResponse,
    ModuleVideosResponse, VideoMetadataUpdate
)
from app.dependencies import get_current_user, get_current_instructor
from app.core.supabase_client import supabase_client
from app.services.storage_service import storage_service

router = APIRouter()


# ============ Video Upload Endpoints ============

@router.post("/videos/upload", response_model=VideoUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    course_id: str = Form(...),
    module_id: str = Form(...),
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_instructor)
):
    """
    Upload a video to a course module
    - Max file size: 500MB
    - Supported formats: MP4, WebM, MOV, AVI, FLV, MKV
    """
    try:
        # Verify course ownership
        course = supabase_client.table("courses").select("instructor_id").eq(
            "id", course_id
        ).single().execute()
        
        if not course.data:
            raise HTTPException(status_code=404, detail="Course not found")
        
        if current_user["role"] != "admin" and course.data["instructor_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized to upload videos to this course")
        
        # Verify module exists in course
        module = supabase_client.table("course_modules").select("id").eq(
            "id", module_id
        ).eq("course_id", course_id).single().execute()
        
        if not module.data:
            raise HTTPException(status_code=404, detail="Module not found in this course")
        
        # Read file content and get size
        file_content = await file.read()
        file_size = len(file_content)
        
        # Get MIME type
        mime_type = file.content_type or "video/mp4"
        filename = file.filename or "video.mp4"
        
        # Reset file pointer for upload
        await file.seek(0)
        
        # Upload video using storage service
        upload_result = storage_service.upload_course_video(
            course_id=course_id,
            module_id=module_id,
            file=file.file,
            filename=filename,
            mime_type=mime_type,
            file_size=file_size,
            user_id=current_user["id"]
        )
        
        if not upload_result["success"]:
            raise HTTPException(status_code=400, detail=upload_result["error"])
        
        # Update video metadata with title and description if provided
        if title or description:
            metadata_update = {}
            if title:
                supabase_client.table("course_videos").update({"title": title}).eq(
                    "video_id", upload_result["video_id"]
                ).execute()
            if description:
                supabase_client.table("course_videos").update({"description": description}).eq(
                    "video_id", upload_result["video_id"]
                ).execute()
        
        return VideoUploadResponse(
            success=True,
            video_id=upload_result["video_id"],
            video_url=upload_result["video_url"],
            file_size=file_size,
            message=upload_result["message"],
            video_data=upload_result.get("video_data")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Video upload failed: {str(e)}"
        )


@router.get("/videos/{video_id}", response_model=CourseVideoResponse)
async def get_video(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get video details"""
    try:
        result = supabase_client.table("course_videos").select("*").eq(
            "video_id", video_id
        ).single().execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Video not found")
        
        video = result.data
        
        # Verify user has access to course
        course = supabase_client.table("courses").select("id").eq(
            "id", video["course_id"]
        ).single().execute()
        
        if not course.data:
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Check if user is enrolled or instructor
        is_enrolled = supabase_client.table("enrollments").select("id").eq(
            "user_id", current_user["id"]
        ).eq("course_id", video["course_id"]).execute()
        
        is_instructor = video["uploaded_by"] == current_user["id"] or current_user["role"] == "admin"
        
        if not is_enrolled.data and not is_instructor:
            raise HTTPException(status_code=403, detail="Not authorized to view this video")
        
        return CourseVideoResponse(**video)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modules/{module_id}/videos", response_model=ModuleVideosResponse)
async def get_module_videos(
    module_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all videos in a module"""
    try:
        # Get module and course info
        module = supabase_client.table("course_modules").select(
            "id, course_id, courses(id)"
        ).eq("id", module_id).single().execute()
        
        if not module.data:
            raise HTTPException(status_code=404, detail="Module not found")
        
        course_id = module.data["course_id"]
        
        # Verify access
        is_enrolled = supabase_client.table("enrollments").select("id").eq(
            "user_id", current_user["id"]
        ).eq("course_id", course_id).execute()
        
        is_instructor = supabase_client.table("courses").select("instructor_id").eq(
            "id", course_id
        ).single().execute()
        
        if not is_enrolled.data and is_instructor.data["instructor_id"] != current_user["id"] and current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Not authorized to view this module")
        
        # Get all videos
        result = supabase_client.table("course_videos").select("*").eq(
            "module_id", module_id
        ).order("created_at", desc=True).execute()
        
        videos = [CourseVideoResponse(**video) for video in result.data]
        total_size = sum(video.file_size for video in videos)
        
        return ModuleVideosResponse(
            videos=videos,
            count=len(videos),
            total_size=total_size
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: str,
    current_user: dict = Depends(get_current_instructor)
):
    """Delete a video (Instructor/Admin only)"""
    try:
        # Get video details
        video = supabase_client.table("course_videos").select(
            "video_id, course_id, module_id, uploaded_by"
        ).eq("video_id", video_id).single().execute()
        
        if not video.data:
            raise HTTPException(status_code=404, detail="Video not found")
        
        video_data = video.data
        
        # Verify ownership
        if current_user["role"] != "admin" and video_data["uploaded_by"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized to delete this video")
        
        # Delete using storage service
        delete_result = storage_service.delete_video(
            video_id=video_id,
            course_id=video_data["course_id"],
            module_id=video_data["module_id"]
        )
        
        if not delete_result["success"]:
            raise HTTPException(status_code=400, detail=delete_result["error"])
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete video: {str(e)}")


@router.put("/videos/{video_id}/metadata", response_model=CourseVideoResponse)
async def update_video_metadata(
    video_id: str,
    metadata: VideoMetadataUpdate,
    current_user: dict = Depends(get_current_instructor)
):
    """Update video metadata (title, description, duration, etc.)"""
    try:
        # Get video details
        video = supabase_client.table("course_videos").select(
            "video_id, uploaded_by"
        ).eq("video_id", video_id).single().execute()
        
        if not video.data:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Verify ownership
        if current_user["role"] != "admin" and video.data["uploaded_by"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized to update this video")
        
        # Update metadata
        update_data = {}
        if metadata.title is not None:
            update_data["title"] = metadata.title
        if metadata.description is not None:
            update_data["description"] = metadata.description
        if metadata.duration is not None:
            update_data["duration"] = metadata.duration
        if metadata.thumbnail_url is not None:
            update_data["thumbnail_url"] = metadata.thumbnail_url
        if metadata.metadata is not None:
            update_data["metadata"] = metadata.metadata
        
        result = supabase_client.table("course_videos").update(update_data).eq(
            "video_id", video_id
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=400, detail="Failed to update video metadata")
        
        return CourseVideoResponse(**result.data[0])
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/courses/{course_id}/videos", response_model=List[CourseVideoResponse])
async def get_course_videos(
    course_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all videos in a course"""
    try:
        # Verify course exists
        course = supabase_client.table("courses").select("id").eq(
            "id", course_id
        ).single().execute()
        
        if not course.data:
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Verify access
        is_enrolled = supabase_client.table("enrollments").select("id").eq(
            "user_id", current_user["id"]
        ).eq("course_id", course_id).execute()
        
        is_instructor = supabase_client.table("courses").select("instructor_id").eq(
            "id", course_id
        ).single().execute()
        
        if not is_enrolled.data and is_instructor.data["instructor_id"] != current_user["id"] and current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Not authorized to view this course")
        
        # Get all videos in course
        result = supabase_client.table("course_videos").select("*").eq(
            "course_id", course_id
        ).order("module_id", desc=True).order("created_at", desc=True).execute()
        
        return [CourseVideoResponse(**video) for video in result.data]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


