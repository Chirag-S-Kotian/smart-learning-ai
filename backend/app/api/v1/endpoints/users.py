from fastapi import APIRouter, HTTPException, status, Depends
from app.schemas.user import UserUpdate, UserProfileResponse
from app.dependencies import (
    get_current_user, get_current_admin,
    get_pagination_params
)
from app.core.supabase_client import supabase_client

router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Get current user's profile with statistics"""
    try:
        # Get enrollment stats for students
        if current_user["role"] == "student":
            enrollments = supabase_client.table("enrollments").select(
                "status", count="exact"
            ).eq("user_id", current_user["id"]).execute()
            
            completed = supabase_client.table("enrollments").select(
                "id", count="exact"
            ).eq("user_id", current_user["id"]).eq("status", "completed").execute()
            
            attempts = supabase_client.table("assessment_attempts").select(
                "score, submitted_at", count="exact"
            ).eq("user_id", current_user["id"]).not_.is_("submitted_at", "null").execute()
            
            avg_score = 0.0
            if attempts.data:
                total_score = sum(float(a.get("score", 0)) for a in attempts.data if a.get("score"))
                avg_score = total_score / len(attempts.data) if attempts.data else 0.0
            
            return UserProfileResponse(
                **current_user,
                enrolled_courses=enrollments.count,
                completed_courses=completed.count,
                total_assessments_taken=attempts.count,
                average_score=round(avg_score, 2)
            )
        
        return UserProfileResponse(**current_user)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch profile: {str(e)}"
        )


@router.put("/me", response_model=UserProfileResponse)
async def update_my_profile(
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update current user's profile"""
    try:
        update_dict = user_data.model_dump(exclude_unset=True)
        
        if not update_dict:
            return UserProfileResponse(**current_user)
        
        result = supabase_client.table("users").update(update_dict).eq(
            "id", current_user["id"]
        ).execute()
        
        return UserProfileResponse(**result.data[0])
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get user profile by ID"""
    try:
        result = supabase_client.table("users").select("*").eq("id", user_id).single().execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserProfileResponse(**result.data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user: {str(e)}"
        )


@router.get("/")
async def list_users(
    pagination: dict = Depends(get_pagination_params),
    role: str = None,
    current_user: dict = Depends(get_current_admin)
):
    """List all users (Admin only)"""
    try:
        query = supabase_client.table("users").select("*", count="exact")
        
        if role:
            query = query.eq("role", role)
        
        query = query.range(
            pagination["offset"],
            pagination["offset"] + pagination["page_size"] - 1
        ).order("created_at", desc=True)
        
        result = query.execute()
        
        return {
            "users": result.data,
            "total": result.count,
            "page": pagination["page"],
            "page_size": pagination["page_size"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin)
):
    """Delete a user (Admin only)"""
    try:
        # Don't allow deleting self
        if user_id == current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Get user's auth_id
        user_result = supabase_client.table("users").select("auth_id").eq("id", user_id).single().execute()
        
        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Delete from database (CASCADE will handle related records)
        supabase_client.table("users").delete().eq("id", user_id).execute()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )