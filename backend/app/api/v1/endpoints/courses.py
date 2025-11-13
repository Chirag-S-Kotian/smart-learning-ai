from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from app.schemas.course import (
    CourseCreate, CourseUpdate, CourseResponse,
    CourseDetailResponse, CourseListResponse,
    CourseModuleCreate, CourseModuleUpdate, CourseModuleResponse
)
from app.dependencies import (
    get_current_user, get_current_instructor,
    get_current_admin, get_pagination_params
)
from app.core.supabase_client import supabase_client

router = APIRouter()


@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    course_data: CourseCreate,
    current_user: dict = Depends(get_current_instructor)
):
    """Create a new course (Instructor/Admin only)"""
    try:
        course_dict = course_data.model_dump()
        course_dict["instructor_id"] = current_user["id"]
        
        result = supabase_client.table("courses").insert(course_dict).execute()
        course = result.data[0]
        
        # Add instructor name
        course["instructor_name"] = current_user["full_name"]
        course["total_students"] = 0
        course["total_modules"] = 0
        course["total_content"] = 0
        
        return course
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create course: {str(e)}"
        )


@router.get("/", response_model=CourseListResponse)
async def list_courses(
    pagination: dict = Depends(get_pagination_params),
    is_published: Optional[bool] = None,
    instructor_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List all courses with pagination and filters"""
    try:
        query = supabase_client.table("courses").select(
            "*, users!courses_instructor_id_fkey(full_name)",
            count="exact"
        )
        
        # Apply filters
        if is_published is not None:
            query = query.eq("is_published", is_published)
        
        if instructor_id:
            query = query.eq("instructor_id", instructor_id)
        
        if search:
            query = query.ilike("title", f"%{search}%")
        
        # For students, only show published courses
        if current_user["role"] == "student":
            query = query.eq("is_published", True)
        
        # Apply pagination
        query = query.range(
            pagination["offset"],
            pagination["offset"] + pagination["page_size"] - 1
        ).order("created_at", desc=True)
        
        result = query.execute()
        
        # Format response
        courses = []
        for course in result.data:
            course_dict = {
                **course,
                "instructor_name": course.get("users", {}).get("full_name") if course.get("users") else None
            }
            # Remove nested user object
            if "users" in course_dict:
                del course_dict["users"]
            courses.append(course_dict)
        
        return CourseListResponse(
            courses=courses,
            total=result.count,
            page=pagination["page"],
            page_size=pagination["page_size"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch courses: {str(e)}"
        )


@router.get("/{course_id}", response_model=CourseDetailResponse)
async def get_course(
    course_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get course details with modules"""
    try:
        # Fetch course
        course_result = supabase_client.table("courses").select(
            "*, users!courses_instructor_id_fkey(full_name)"
        ).eq("id", course_id).single().execute()
        
        course = course_result.data
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Check access for unpublished courses
        if not course["is_published"] and current_user["role"] == "student":
            if course["instructor_id"] != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Course not accessible"
                )
        
        # Fetch modules
        modules_result = supabase_client.table("course_modules").select("*").eq(
            "course_id", course_id
        ).order("order_index").execute()
        
        # Get enrollment count
        enrollment_count = supabase_client.table("enrollments").select(
            "id", count="exact"
        ).eq("course_id", course_id).eq("status", "active").execute()
        
        course["instructor_name"] = course.get("users", {}).get("full_name")
        course["modules"] = modules_result.data
        course["total_students"] = enrollment_count.count
        course["total_modules"] = len(modules_result.data)
        
        if "users" in course:
            del course["users"]
        
        return course
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch course: {str(e)}"
        )


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    course_data: CourseUpdate,
    current_user: dict = Depends(get_current_instructor)
):
    """Update course (Instructor/Admin only)"""
    try:
        # Check ownership or admin
        course_result = supabase_client.table("courses").select("instructor_id").eq(
            "id", course_id
        ).single().execute()
        
        course = course_result.data
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        if current_user["role"] != "admin" and course["instructor_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this course"
            )
        
        # Update course
        update_dict = course_data.model_dump(exclude_unset=True)
        
        result = supabase_client.table("courses").update(update_dict).eq(
            "id", course_id
        ).execute()
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update course: {str(e)}"
        )


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: str,
    current_user: dict = Depends(get_current_instructor)
):
    """Delete course (Instructor/Admin only)"""
    try:
        # Check ownership or admin
        course_result = supabase_client.table("courses").select("instructor_id").eq(
            "id", course_id
        ).single().execute()
        
        course = course_result.data
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        if current_user["role"] != "admin" and course["instructor_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this course"
            )
        
        # Delete course (CASCADE will handle related records)
        supabase_client.table("courses").delete().eq("id", course_id).execute()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete course: {str(e)}"
        )


@router.post("/{course_id}/modules", response_model=CourseModuleResponse, status_code=status.HTTP_201_CREATED)
async def create_module(
    course_id: str,
    module_data: CourseModuleCreate,
    current_user: dict = Depends(get_current_instructor)
):
    """Add a module to a course"""
    try:
        # Check course ownership
        course_result = supabase_client.table("courses").select("instructor_id").eq(
            "id", course_id
        ).single().execute()
        
        course = course_result.data
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        if current_user["role"] != "admin" and course["instructor_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this course"
            )
        
        module_dict = module_data.model_dump()
        module_dict["course_id"] = course_id
        
        result = supabase_client.table("course_modules").insert(module_dict).execute()
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create module: {str(e)}"
        )


@router.post("/{course_id}/enroll", status_code=status.HTTP_201_CREATED)
async def enroll_in_course(
    course_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Enroll current user in a course"""
    try:
        # Check if course exists and is published
        course_result = supabase_client.table("courses").select(
            "id, is_published, enrollment_open"
        ).eq("id", course_id).single().execute()
        
        course = course_result.data
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        if not course["is_published"] or not course["enrollment_open"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course enrollment is not open"
            )
        
        # Check if already enrolled
        existing = supabase_client.table("enrollments").select("id").eq(
            "user_id", current_user["id"]
        ).eq("course_id", course_id).execute()
        
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already enrolled in this course"
            )
        
        # Create enrollment
        enrollment_data = {
            "user_id": current_user["id"],
            "course_id": course_id,
            "status": "active"
        }
        
        result = supabase_client.table("enrollments").insert(enrollment_data).execute()
        
        return {
            "message": "Successfully enrolled in course",
            "enrollment": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enrollment failed: {str(e)}"
        )


@router.get("/my/enrollments")
async def get_my_enrollments(
    current_user: dict = Depends(get_current_user)
):
    """Get current user's enrolled courses"""
    try:
        result = supabase_client.table("enrollments").select(
            "*, courses(*)"
        ).eq("user_id", current_user["id"]).execute()
        
        return {
            "enrollments": result.data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch enrollments: {str(e)}"
        )