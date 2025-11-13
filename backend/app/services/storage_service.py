import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, BinaryIO
from app.config import settings
from app.core.supabase_client import supabase_client


class StorageService:
    """
    Storage service for handling file uploads to Supabase Storage
    Supports video uploads up to 500MB per file
    """
    
    # File size limits in bytes
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB
    MAX_CHUNK_SIZE = 5 * 1024 * 1024    # 5MB for chunked uploads
    
    # Supported video formats
    SUPPORTED_VIDEO_FORMATS = [
        'video/mp4',
        'video/webm',
        'video/quicktime',
        'video/x-msvideo',
        'video/x-flv',
        'video/x-matroska'
    ]
    
    SUPPORTED_VIDEO_EXTENSIONS = [
        '.mp4', '.webm', '.mov', '.avi', '.flv', '.mkv', '.m4v'
    ]
    
    def __init__(self):
        self.bucket_name = settings.STORAGE_BUCKET
        self.max_video_size = self.MAX_VIDEO_SIZE
    
    def _validate_video_file(self, file_size: int, mime_type: str, filename: str) -> tuple[bool, str]:
        """
        Validate video file before upload
        
        Args:
            file_size: Size of file in bytes
            mime_type: MIME type of the file
            filename: Original filename
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        if file_size > self.max_video_size:
            return False, f"File size exceeds 500MB limit. Size: {file_size / (1024*1024):.2f}MB"
        
        if file_size == 0:
            return False, "File is empty"
        
        # Check MIME type
        if mime_type not in self.SUPPORTED_VIDEO_FORMATS:
            return False, f"Unsupported video format: {mime_type}"
        
        # Check file extension
        _, ext = os.path.splitext(filename)
        if ext.lower() not in self.SUPPORTED_VIDEO_EXTENSIONS:
            return False, f"Unsupported video extension: {ext}"
        
        return True, ""
    
    def upload_course_video(
        self,
        course_id: str,
        module_id: str,
        file: BinaryIO,
        filename: str,
        mime_type: str,
        file_size: int,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Upload a video file to course module
        
        Args:
            course_id: Course ID
            module_id: Module ID
            file: File object to upload
            filename: Original filename
            mime_type: MIME type of file
            file_size: Size of file in bytes
            user_id: ID of user uploading
            
        Returns:
            Dictionary with upload status, video URL, and metadata
        """
        try:
            # Validate video
            is_valid, error_msg = self._validate_video_file(file_size, mime_type, filename)
            if not is_valid:
                return {
                    "success": False,
                    "error": error_msg,
                    "video_id": None,
                    "video_url": None
                }
            
            # Generate unique video ID and filename
            video_id = str(uuid.uuid4())
            _, ext = os.path.splitext(filename)
            storage_filename = f"{video_id}{ext}"
            
            # Create path in storage
            storage_path = f"courses/{course_id}/modules/{module_id}/{storage_filename}"
            
            # Upload file to Supabase Storage
            file.seek(0)  # Ensure we're at the beginning
            file_content = file.read()
            
            response = supabase_client.storage.from_(self.bucket_name).upload(
                storage_path,
                file_content,
                {
                    "content-type": mime_type,
                    "cacheControl": "3600"
                }
            )
            
            # Get public URL
            video_url = supabase_client.storage.from_(self.bucket_name).get_public_url(storage_path)
            
            # Save video metadata to database
            video_metadata = {
                "video_id": video_id,
                "course_id": course_id,
                "module_id": module_id,
                "original_filename": filename,
                "storage_filename": storage_filename,
                "storage_path": storage_path,
                "file_size": file_size,
                "mime_type": mime_type,
                "video_url": video_url,
                "uploaded_by": user_id,
                "status": "uploaded",
                "duration": None,  # Will be set by video processing
                "thumbnail_url": None,
                "metadata": {}
            }
            
            db_result = supabase_client.table("course_videos").insert(video_metadata).execute()
            
            if not db_result.data:
                raise Exception("Failed to save video metadata to database")
            
            return {
                "success": True,
                "video_id": video_id,
                "video_url": video_url,
                "video_data": db_result.data[0],
                "file_size": file_size,
                "message": f"Video uploaded successfully: {filename}"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Upload failed: {str(e)}",
                "video_id": None,
                "video_url": None
            }
    
    def get_video_url(self, video_id: str) -> Optional[str]:
        """
        Get public URL for a video
        
        Args:
            video_id: Video ID
            
        Returns:
            Public URL or None if not found
        """
        try:
            result = supabase_client.table("course_videos").select("video_url").eq(
                "video_id", video_id
            ).single().execute()
            
            if result.data:
                return result.data["video_url"]
            return None
        except Exception:
            return None
    
    def delete_video(self, video_id: str, course_id: str, module_id: str) -> Dict[str, Any]:
        """
        Delete a video file and metadata
        
        Args:
            video_id: Video ID
            course_id: Course ID
            module_id: Module ID
            
        Returns:
            Dictionary with deletion status
        """
        try:
            # Get video metadata
            result = supabase_client.table("course_videos").select("storage_path").eq(
                "video_id", video_id
            ).single().execute()
            
            if not result.data:
                return {
                    "success": False,
                    "error": "Video not found"
                }
            
            storage_path = result.data["storage_path"]
            
            # Delete from storage
            supabase_client.storage.from_(self.bucket_name).remove([storage_path])
            
            # Delete from database
            supabase_client.table("course_videos").delete().eq("video_id", video_id).execute()
            
            return {
                "success": True,
                "message": f"Video {video_id} deleted successfully"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Deletion failed: {str(e)}"
            }
    
    def get_module_videos(self, course_id: str, module_id: str) -> Dict[str, Any]:
        """
        Get all videos in a module
        
        Args:
            course_id: Course ID
            module_id: Module ID
            
        Returns:
            List of videos in the module
        """
        try:
            result = supabase_client.table("course_videos").select("*").eq(
                "course_id", course_id
            ).eq("module_id", module_id).order("created_at", desc=True).execute()
            
            return {
                "success": True,
                "videos": result.data,
                "count": len(result.data)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "videos": [],
                "count": 0
            }
    
    def update_video_metadata(self, video_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update video metadata (duration, thumbnail, etc.)
        
        Args:
            video_id: Video ID
            metadata: Metadata to update
            
        Returns:
            Updated video data
        """
        try:
            update_data = {
                "metadata": metadata,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = supabase_client.table("course_videos").update(update_data).eq(
                "video_id", video_id
            ).execute()
            
            if result.data:
                return {
                    "success": True,
                    "video_data": result.data[0]
                }
            else:
                return {
                    "success": False,
                    "error": "Video not found"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
storage_service = StorageService()


