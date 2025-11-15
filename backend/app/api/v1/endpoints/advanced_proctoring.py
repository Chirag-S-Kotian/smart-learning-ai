"""
Advanced Proctoring Endpoints
- Eye tracking monitoring
- Noise/audio detection
- Face recognition and identity verification
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import Optional
from app.dependencies import get_current_user
from app.services.advanced_proctoring import (
    AdvancedProctoringService,
    EyeTrackingService,
    NoiseDetectionService,
    FaceRecognitionService
)
from app.utils.exceptions import AppError

router = APIRouter(prefix="/api/v1/advanced-proctoring", tags=["advanced-proctoring"])


@router.post("/sessions/{session_id}/start-advanced-monitoring")
async def start_advanced_monitoring(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Start advanced proctoring with eye tracking, noise detection, and face recognition
    
    Args:
        session_id: Proctoring session ID
        
    Returns:
        Status of advanced monitoring activation
    """
    try:
        result = await AdvancedProctoringService.start_advanced_monitoring(
            session_id=session_id,
            user_id=current_user.get("id"),
            assessment_id=""
        )
        return result
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/process-frame")
async def process_frame_with_advanced_features(
    session_id: str,
    frame_data: str = Body(..., embed=True),
    audio_data: Optional[str] = Body(None, embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Process frame with all advanced proctoring features
    
    Args:
        session_id: Proctoring session ID
        frame_data: Base64 encoded frame
        audio_data: Optional base64 encoded audio
        
    Returns:
        Analysis results from all features
    """
    try:
        result = await AdvancedProctoringService.process_advanced_frame(
            session_id=session_id,
            frame_data=frame_data,
            audio_data=audio_data
        )
        return result
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EYE TRACKING ENDPOINTS
# ============================================================================

@router.post("/eye-tracking/analyze")
async def analyze_eye_gaze(
    session_id: str = Body(..., embed=True),
    frame_data: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze eye gaze from frame
    
    Args:
        session_id: Proctoring session ID
        frame_data: Base64 encoded frame
        
    Returns:
        Eye tracking analysis
    """
    try:
        result = await EyeTrackingService.analyze_eye_gaze(
            session_id=session_id,
            frame_data=frame_data
        )
        return result
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/eye-tracking/analytics/{session_id}")
async def get_eye_tracking_analytics(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive eye tracking analytics for session
    
    Args:
        session_id: Proctoring session ID
        
    Returns:
        Eye tracking analytics and statistics
    """
    try:
        analytics = await EyeTrackingService.get_eye_tracking_analytics(session_id)
        return analytics
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NOISE DETECTION ENDPOINTS
# ============================================================================

@router.post("/noise-detection/analyze")
async def analyze_audio(
    session_id: str = Body(..., embed=True),
    audio_data: str = Body(..., embed=True),
    duration_seconds: float = Body(5.0, embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze audio for suspicious patterns
    
    Args:
        session_id: Proctoring session ID
        audio_data: Base64 encoded audio
        duration_seconds: Duration of audio sample
        
    Returns:
        Audio analysis results
    """
    try:
        result = await NoiseDetectionService.analyze_audio(
            session_id=session_id,
            audio_data=audio_data,
            duration_seconds=duration_seconds
        )
        return result
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/noise-detection/analytics/{session_id}")
async def get_audio_analytics(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive audio analytics for session
    
    Args:
        session_id: Proctoring session ID
        
    Returns:
        Audio analytics and statistics
    """
    try:
        analytics = await NoiseDetectionService.get_audio_analytics(session_id)
        return analytics
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FACE RECOGNITION ENDPOINTS
# ============================================================================

@router.post("/face-recognition/verify")
async def verify_student_identity(
    session_id: str = Body(..., embed=True),
    frame_data: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Verify student identity and detect spoofing attempts
    
    Args:
        session_id: Proctoring session ID
        frame_data: Base64 encoded frame
        
    Returns:
        Identity verification results
    """
    try:
        result = await FaceRecognitionService.verify_student_identity(
            session_id=session_id,
            user_id=current_user.get("id"),
            frame_data=frame_data
        )
        return result
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/face-recognition/analytics/{session_id}")
async def get_face_verification_analytics(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive face verification analytics for session
    
    Args:
        session_id: Proctoring session ID
        
    Returns:
        Face verification analytics and statistics
    """
    try:
        analytics = await FaceRecognitionService.get_face_verification_analytics(session_id)
        return analytics
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# COMPREHENSIVE ANALYTICS
# ============================================================================

@router.get("/analytics/{session_id}")
async def get_comprehensive_analytics(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive analytics for all advanced proctoring features
    
    Args:
        session_id: Proctoring session ID
        
    Returns:
        Combined analytics from all features
    """
    try:
        analytics = await AdvancedProctoringService.get_comprehensive_analytics(session_id)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
