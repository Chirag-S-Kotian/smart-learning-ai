"""
Certificate and Badge Management Endpoints
Handles certificate generation, badge awards, and verification
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List
from app.services.certificate_service import certificate_service
from app.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/certificates", tags=["certificates"])


@router.post("/course/{course_id}/complete")
async def generate_course_certificate(
    course_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate certificate for course completion
    
    Args:
        course_id: Course ID
        
    Returns:
        Certificate data with verification code
    """
    try:
        result = await certificate_service.generate_course_completion_certificate(
            user_id=current_user["id"],
            course_id=course_id
        )
        return {
            "success": True,
            "data": result,
            "message": "Certificate generated successfully"
        }
    except Exception as e:
        logger.error(f"Error generating course certificate: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/exam/{assessment_id}/complete")
async def generate_exam_certificate(
    assessment_id: str,
    score: float = Query(...),
    percentage: float = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate certificate for exam completion
    
    Args:
        assessment_id: Assessment ID
        score: Raw score obtained
        percentage: Score percentage (0-100)
        
    Returns:
        Certificate data with verification code and grade
    """
    try:
        if not 0 <= percentage <= 100:
            raise ValueError("Percentage must be between 0 and 100")
        
        result = await certificate_service.generate_exam_certificate(
            user_id=current_user["id"],
            assessment_id=assessment_id,
            score=score,
            percentage=percentage
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "data": result,
            "message": "Exam certificate generated successfully"
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error generating exam certificate: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/verify/{verification_code}")
async def verify_certificate(
    verification_code: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify a certificate by verification code
    
    Args:
        verification_code: Certificate verification code
        
    Returns:
        Verification result with certificate data
    """
    try:
        result = certificate_service.verify_certificate(verification_code)
        
        if not result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certificate not found"
            )
        
        return {
            "success": True,
            "data": result["certificate"],
            "message": result["message"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying certificate: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/my-certificates")
async def get_my_certificates(
    certificate_type: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's certificates
    
    Args:
        certificate_type: Filter by type (course_completion, exam_completion)
        skip: Number of records to skip
        limit: Number of records to return
        
    Returns:
        List of user certificates
    """
    try:
        from app.core.supabase_client import supabase_client
        
        query = supabase_client.table("certificates").select(
            "id, certificate_number, title, type, issued_date, grade, percentage"
        ).eq("user_id", current_user["id"])
        
        if certificate_type:
            query = query.eq("type", certificate_type)
        
        result = query.order("issued_date", desc=True).range(skip, skip + limit - 1).execute()
        
        return {
            "success": True,
            "data": result.data or [],
            "count": len(result.data or [])
        }
    except Exception as e:
        logger.error(f"Error fetching certificates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/public/{user_id}")
async def get_user_certificates_public(
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Get user's public certificates (no authentication required)
    
    Args:
        user_id: User ID
        skip: Number of records to skip
        limit: Number of records to return
        
    Returns:
        List of user certificates (only verified/public ones)
    """
    try:
        from app.core.supabase_client import supabase_client
        
        result = supabase_client.table("certificates").select(
            "id, certificate_number, title, type, issued_date, grade, percentage, users(full_name)"
        ).eq("user_id", user_id).eq("is_verified", True).order(
            "issued_date", desc=True
        ).range(skip, skip + limit - 1).execute()
        
        certificates = result.data or []
        
        # Add user name to each certificate
        for cert in certificates:
            cert["user_name"] = cert.get("users", {}).get("full_name", "")
            if "users" in cert:
                del cert["users"]
        
        return {
            "success": True,
            "data": certificates,
            "count": len(certificates)
        }
    except Exception as e:
        logger.error(f"Error fetching public certificates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Badge Endpoints

@router.post("/badges/{badge_key}/award")
async def award_badge(
    badge_key: str,
    target_user_id: str = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Award a badge to a user (admin only, or self)
    
    Args:
        badge_key: Badge identifier
        target_user_id: User to award badge to (default: current user)
        
    Returns:
        Badge award data
    """
    try:
        user_id = target_user_id or current_user["id"]
        
        # Authorization check (allow self-award or admin)
        if user_id != current_user["id"]:
            # Check if current user is admin
            if current_user.get("role") != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
        
        result = await certificate_service.award_badge(user_id, badge_key)
        
        if result.get("already_awarded"):
            return {
                "success": True,
                "data": result,
                "message": "User already has this badge"
            }
        
        return {
            "success": True,
            "data": result,
            "message": "Badge awarded successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error awarding badge: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/badges/list")
async def list_available_badges():
    """
    Get list of all available badges with definitions
    
    Returns:
        Badge definitions and requirements
    """
    try:
        badges_info = []
        for key, badge_def in certificate_service.BADGES.items():
            badges_info.append({
                "key": key,
                "name": badge_def["name"],
                "description": badge_def["description"],
                "icon": badge_def["icon"],
                "category": badge_def["category"],
                "criteria": badge_def.get("criteria", {})
            })
        
        return {
            "success": True,
            "data": badges_info,
            "count": len(badges_info)
        }
    except Exception as e:
        logger.error(f"Error fetching badges: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/badges/my-badges")
async def get_my_badges(
    category: str = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's earned badges
    
    Args:
        category: Filter by category (milestone, achievement)
        
    Returns:
        List of user badges
    """
    try:
        badges = await certificate_service.get_user_badges(current_user["id"])
        
        if category:
            badges = [b for b in badges if b.get("category") == category]
        
        return {
            "success": True,
            "data": badges,
            "count": len(badges)
        }
    except Exception as e:
        logger.error(f"Error fetching user badges: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/achievements/summary")
async def get_achievement_summary(
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's complete achievement summary
    
    Returns:
        Comprehensive achievement data with certificates and badges
    """
    try:
        achievements = await certificate_service.get_user_achievements(current_user["id"])
        
        return {
            "success": True,
            "data": achievements,
            "message": "Achievement summary retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error fetching achievement summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/achievements/public/{user_id}")
async def get_public_achievement_summary(user_id: str):
    """
    Get user's public achievement summary
    
    Args:
        user_id: User ID
        
    Returns:
        Public achievement data
    """
    try:
        from app.core.supabase_client import supabase_client
        
        # Get public achievement data
        achievements = await certificate_service.get_user_achievements(user_id)
        
        # Filter to only show public data
        public_data = {
            "user_id": achievements["user_id"],
            "total_certificates": achievements["total_certificates"],
            "course_certificates": achievements["course_certificates"],
            "exam_certificates": achievements["exam_certificates"],
            "total_badges": achievements["total_badges"],
            "average_exam_score": achievements["average_exam_score"],
            "badge_categories": achievements["badge_categories"],
            "badges": achievements["badges"]
        }
        
        return {
            "success": True,
            "data": public_data,
            "message": "Public achievement summary retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error fetching public achievement summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/badges/{user_id}/public")
async def get_user_badges_public(user_id: str):
    """
    Get user's public badges (no authentication required)
    
    Args:
        user_id: User ID
        
    Returns:
        List of user badges
    """
    try:
        badges = await certificate_service.get_user_badges(user_id)
        
        return {
            "success": True,
            "data": badges,
            "count": len(badges)
        }
    except Exception as e:
        logger.error(f"Error fetching public badges: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
