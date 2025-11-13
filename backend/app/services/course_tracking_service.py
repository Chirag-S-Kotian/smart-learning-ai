"""
Course Watching and Progress Tracking Service
Handles tracking of student video watching and course progress
"""
from uuid import uuid4
from datetime import datetime
from typing import Optional, Dict, Any
from app.core.supabase_client import supabase_client


class CourseTrackingService:
    """
    Service for tracking student course watching and progress
    """
    
    def __init__(self):
        pass
    
    # ============ Video Watching Tracking ============
    
    def start_video_watch(
        self,
        user_id: str,
        video_id: str,
        course_id: str,
        module_id: str,
        total_video_duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Start tracking a video watch session
        
        Args:
            user_id: User ID
            video_id: Video ID
            course_id: Course ID
            module_id: Module ID
            total_video_duration: Total video duration in seconds
            
        Returns:
            Session data with session_id
        """
        try:
            session_id = str(uuid4())
            
            watch_data = {
                "user_id": user_id,
                "video_id": video_id,
                "course_id": course_id,
                "module_id": module_id,
                "watch_start_time": datetime.utcnow().isoformat(),
                "total_video_duration": total_video_duration,
                "session_id": session_id,
                "view_count": 1
            }
            
            result = supabase_client.table("video_watching").insert(watch_data).execute()
            
            if result.data:
                return {
                    "success": True,
                    "session_id": session_id,
                    "watch_id": result.data[0]["id"]
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to start video watch session"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_video_watch(
        self,
        watch_id: str,
        duration_watched: int,
        watch_percentage: float,
        playback_speed: float = 1.0
    ) -> Dict[str, Any]:
        """
        Update video watch progress
        
        Args:
            watch_id: Watch record ID
            duration_watched: Seconds watched
            watch_percentage: Percentage of video watched (0-100)
            playback_speed: Playback speed multiplier
            
        Returns:
            Updated watch data
        """
        try:
            update_data = {
                "duration_watched": duration_watched,
                "watch_percentage": watch_percentage,
                "playback_speed": playback_speed,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = supabase_client.table("video_watching").update(update_data).eq(
                "id", watch_id
            ).execute()
            
            if result.data:
                return {
                    "success": True,
                    "watch_data": result.data[0]
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to update video watch"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def complete_video_watch(
        self,
        watch_id: str,
        duration_watched: int,
        watch_percentage: float
    ) -> Dict[str, Any]:
        """
        Mark a video watch as completed
        
        Args:
            watch_id: Watch record ID
            duration_watched: Total seconds watched
            watch_percentage: Final watch percentage
            
        Returns:
            Completed watch data
        """
        try:
            # Check if already marked as complete
            existing = supabase_client.table("video_watching").select("is_completed").eq(
                "id", watch_id
            ).single().execute()
            
            if existing.data and existing.data["is_completed"]:
                return {
                    "success": True,
                    "message": "Video already marked as complete",
                    "watch_data": existing.data
                }
            
            # Mark as complete only if watched >= 80%
            is_completed = watch_percentage >= 80
            
            update_data = {
                "is_completed": is_completed,
                "duration_watched": duration_watched,
                "watch_percentage": watch_percentage,
                "watch_end_time": datetime.utcnow().isoformat(),
                "completion_date": datetime.utcnow().isoformat() if is_completed else None
            }
            
            result = supabase_client.table("video_watching").update(update_data).eq(
                "id", watch_id
            ).execute()
            
            if result.data:
                return {
                    "success": True,
                    "is_completed": is_completed,
                    "watch_data": result.data[0]
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to complete video watch"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user_video_watch_stats(
        self,
        user_id: str,
        course_id: str
    ) -> Dict[str, Any]:
        """
        Get video watching statistics for user in a course
        
        Args:
            user_id: User ID
            course_id: Course ID
            
        Returns:
            Video watch statistics
        """
        try:
            result = supabase_client.table("video_watching").select("*").eq(
                "user_id", user_id
            ).eq("course_id", course_id).execute()
            
            videos = result.data or []
            total_videos_watched = sum(1 for v in videos if v["is_completed"])
            total_duration_watched = sum(v["duration_watched"] or 0 for v in videos)
            avg_watch_percentage = (
                sum(v["watch_percentage"] or 0 for v in videos) / len(videos)
                if videos else 0
            )
            
            return {
                "success": True,
                "total_videos_started": len(videos),
                "total_videos_completed": total_videos_watched,
                "total_duration_watched": total_duration_watched,
                "average_watch_percentage": round(avg_watch_percentage, 2),
                "videos": videos
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    # ============ Course Progress Tracking ============
    
    def init_course_progress(
        self,
        user_id: str,
        course_id: str,
        enrollment_id: str
    ) -> Dict[str, Any]:
        """
        Initialize course progress tracking for a student
        
        Args:
            user_id: User ID
            course_id: Course ID
            enrollment_id: Enrollment ID
            
        Returns:
            Created progress record
        """
        try:
            # Count total modules and videos in course
            modules_result = supabase_client.table("course_modules").select("id").eq(
                "course_id", course_id
            ).execute()
            total_modules = len(modules_result.data or [])
            
            videos_result = supabase_client.table("course_videos").select("id").eq(
                "course_id", course_id
            ).execute()
            total_videos = len(videos_result.data or [])
            
            assessments_result = supabase_client.table("assessments").select("id").eq(
                "course_id", course_id
            ).execute()
            total_assessments = len(assessments_result.data or [])
            
            progress_data = {
                "user_id": user_id,
                "course_id": course_id,
                "enrollment_id": enrollment_id,
                "total_modules": total_modules,
                "total_videos": total_videos,
                "total_assessments": total_assessments,
                "course_status": "in_progress"
            }
            
            result = supabase_client.table("course_progress").insert(progress_data).execute()
            
            if result.data:
                return {
                    "success": True,
                    "progress_id": result.data[0]["id"],
                    "progress_data": result.data[0]
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to initialize course progress"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_course_progress(
        self,
        user_id: str,
        course_id: str,
        videos_watched: Optional[int] = None,
        assessments_passed: Optional[int] = None,
        time_spent: Optional[int] = None,
        current_module_id: Optional[str] = None,
        current_video_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update course progress
        
        Args:
            user_id: User ID
            course_id: Course ID
            videos_watched: Number of videos watched
            assessments_passed: Number of assessments passed
            time_spent: Additional time spent in seconds
            current_module_id: Current module ID being viewed
            current_video_id: Current video ID being watched
            
        Returns:
            Updated progress data
        """
        try:
            # Get current progress
            current = supabase_client.table("course_progress").select("*").eq(
                "user_id", user_id
            ).eq("course_id", course_id).single().execute()
            
            if not current.data:
                return {
                    "success": False,
                    "error": "Course progress not found. Initialize first."
                }
            
            progress = current.data
            
            # Update fields
            update_data = {
                "last_accessed": datetime.utcnow().isoformat()
            }
            
            if videos_watched is not None:
                update_data["videos_watched"] = videos_watched
            
            if assessments_passed is not None:
                update_data["assessments_passed"] = assessments_passed
            
            if time_spent is not None:
                update_data["time_spent"] = (progress.get("time_spent", 0) or 0) + time_spent
            
            if current_module_id:
                update_data["current_module_id"] = current_module_id
            
            if current_video_id:
                update_data["current_video_id"] = current_video_id
            
            # Calculate overall completion percentage
            total_items = (progress.get("total_modules", 0) or 0) + (progress.get("total_videos", 0) or 0) + (progress.get("total_assessments", 0) or 0)
            if total_items > 0:
                completed_items = (progress.get("completed_modules", 0) or 0) + (update_data.get("videos_watched", progress.get("videos_watched", 0)) or 0) + (update_data.get("assessments_passed", progress.get("assessments_passed", 0)) or 0)
                update_data["overall_completion_percentage"] = round((completed_items / total_items) * 100, 2)
            
            result = supabase_client.table("course_progress").update(update_data).eq(
                "user_id", user_id
            ).eq("course_id", course_id).execute()
            
            if result.data:
                return {
                    "success": True,
                    "progress_data": result.data[0]
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to update course progress"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_course_progress(
        self,
        user_id: str,
        course_id: str
    ) -> Dict[str, Any]:
        """
        Get course progress for a user
        
        Args:
            user_id: User ID
            course_id: Course ID
            
        Returns:
            Course progress data
        """
        try:
            result = supabase_client.table("course_progress").select("*").eq(
                "user_id", user_id
            ).eq("course_id", course_id).single().execute()
            
            if result.data:
                return {
                    "success": True,
                    "progress_data": result.data
                }
            else:
                return {
                    "success": False,
                    "error": "Course progress not found"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    # ============ Module Progress Tracking ============
    
    def init_module_progress(
        self,
        user_id: str,
        module_id: str,
        course_id: str
    ) -> Dict[str, Any]:
        """
        Initialize module progress tracking
        
        Args:
            user_id: User ID
            module_id: Module ID
            course_id: Course ID
            
        Returns:
            Created module progress record
        """
        try:
            # Count total content items and assessments in module
            content_result = supabase_client.table("content_items").select("id").eq(
                "module_id", module_id
            ).execute()
            total_content_items = len(content_result.data or [])
            
            videos_result = supabase_client.table("course_videos").select("id").eq(
                "module_id", module_id
            ).execute()
            total_videos = len(videos_result.data or [])
            
            assessments_result = supabase_client.table("assessments").select("id").eq(
                "module_id", module_id
            ).execute()
            total_assessments = len(assessments_result.data or [])
            
            progress_data = {
                "user_id": user_id,
                "module_id": module_id,
                "course_id": course_id,
                "total_content_items": total_content_items,
                "total_videos": total_videos,
                "total_assessments": total_assessments
            }
            
            result = supabase_client.table("module_progress").insert(progress_data).execute()
            
            if result.data:
                return {
                    "success": True,
                    "progress_data": result.data[0]
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to initialize module progress"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_module_progress(
        self,
        user_id: str,
        module_id: str
    ) -> Dict[str, Any]:
        """
        Get module progress for a user
        
        Args:
            user_id: User ID
            module_id: Module ID
            
        Returns:
            Module progress data
        """
        try:
            result = supabase_client.table("module_progress").select("*").eq(
                "user_id", user_id
            ).eq("module_id", module_id).single().execute()
            
            if result.data:
                return {
                    "success": True,
                    "progress_data": result.data
                }
            else:
                return {
                    "success": False,
                    "error": "Module progress not found"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user_all_courses_progress(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get progress for all courses a user is enrolled in
        
        Args:
            user_id: User ID
            
        Returns:
            List of all course progress
        """
        try:
            result = supabase_client.table("course_progress").select("*").eq(
                "user_id", user_id
            ).execute()
            
            courses = result.data or []
            
            return {
                "success": True,
                "total_courses": len(courses),
                "courses_progress": courses,
                "average_completion": round(
                    sum(c.get("overall_completion_percentage", 0) or 0 for c in courses) / len(courses),
                    2
                ) if courses else 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
course_tracking_service = CourseTrackingService()
