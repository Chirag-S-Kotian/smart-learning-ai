"""
Unified Proctoring Endpoints - Supports both manual snapshot uploads and real-time WebSocket streaming
"""

from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, WebSocket, WebSocketDisconnect
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import json
import logging

from app.dependencies import get_current_user, get_current_instructor
from app.core.supabase_client import supabase_client
from app.services.proctoring_service import ProctoringService, realtime_proctoring_manager
import base64

logger = logging.getLogger(__name__)
router = APIRouter()


class ProctoringSessionCreate(BaseModel):
    attempt_id: str


class SnapshotUpload(BaseModel):
    session_id: str
    image_data: str  # base64 encoded image


class ProctoringAlert(BaseModel):
    alert_type: str
    severity: str
    description: str


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_proctoring_session(
    session_data: ProctoringSessionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Start a new proctoring session for an assessment attempt"""
    try:
        # Verify attempt belongs to current user
        attempt_result = supabase_client.table("assessment_attempts").select(
            "id, user_id, assessment_id"
        ).eq("id", session_data.attempt_id).single().execute()
        
        attempt = attempt_result.data
        
        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment attempt not found"
            )
        
        if attempt["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this attempt"
            )
        
        # Check if session already exists
        existing = supabase_client.table("proctoring_sessions").select("id").eq(
            "attempt_id", session_data.attempt_id
        ).execute()
        
        if existing.data:
            return {
                "message": "Session already exists",
                "session": existing.data[0]
            }
        
        # Create new session
        session_dict = {
            "attempt_id": session_data.attempt_id,
            "user_id": current_user["id"],
            "status": "active"
        }
        
        result = supabase_client.table("proctoring_sessions").insert(session_dict).execute()
        
        return {
            "message": "Proctoring session started",
            "session": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create proctoring session: {str(e)}"
        )


@router.post("/sessions/{session_id}/snapshot")
async def upload_snapshot(
    session_id: str,
    snapshot_data: SnapshotUpload,
    current_user: dict = Depends(get_current_user)
):
    """Upload a proctoring snapshot for AI analysis"""
    try:
        # Verify session belongs to current user
        session_result = supabase_client.table("proctoring_sessions").select(
            "id, user_id, attempt_id"
        ).eq("id", session_id).single().execute()
        
        session = session_result.data
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proctoring session not found"
            )
        
        if session["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this session"
            )
        
        # Upload image to Supabase Storage
        image_bytes = base64.b64decode(
            snapshot_data.image_data.split(',')[1] if ',' in snapshot_data.image_data else snapshot_data.image_data
        )
        
        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"proctoring/{session_id}/{timestamp}.jpg"
        
        # Upload to Supabase Storage
        storage_result = supabase_client.storage.from_("lms-storage").upload(
            filename,
            image_bytes,
            {"content-type": "image/jpeg"}
        )
        
        # Get public URL
        snapshot_url = supabase_client.storage.from_("lms-storage").get_public_url(filename)
        
        # Analyze image with Gemini AI
        analysis = await gemini_client.analyze_proctoring_image(snapshot_data.image_data)
        
        # Save snapshot record
        snapshot_record = {
            "session_id": session_id,
            "snapshot_url": snapshot_url,
            "faces_detected": analysis["faces_detected"],
            "analysis_result": analysis,
            "has_alert": analysis["multiple_faces"] or analysis["no_face_detected"] or analysis["suspicious_activity"],
            "confidence_score": analysis["confidence"]
        }
        
        snapshot_result = supabase_client.table("proctoring_snapshots").insert(
            snapshot_record
        ).execute()
        
        snapshot = snapshot_result.data[0]
        
        # Create alert if suspicious activity detected
        if snapshot_record["has_alert"]:
            alert_type = None
            severity = "medium"
            description = analysis["description"]
            
            if analysis["no_face_detected"]:
                alert_type = "no_face"
                severity = "high"
            elif analysis["multiple_faces"]:
                alert_type = "multiple_faces"
                severity = "high"
            elif analysis["suspicious_activity"]:
                alert_type = "suspicious_activity"
                severity = "medium"
            
            alert_record = {
                "session_id": session_id,
                "snapshot_id": snapshot["id"],
                "alert_type": alert_type,
                "severity": severity,
                "description": description
            }
            
            supabase_client.table("proctoring_alerts").insert(alert_record).execute()
            
            # Update session alert count
            supabase_client.rpc(
                "increment",
                {
                    "table_name": "proctoring_sessions",
                    "row_id": session_id,
                    "column_name": "total_alerts"
                }
            ).execute()
            
            # Update attempt violation count
            supabase_client.rpc(
                "increment",
                {
                    "table_name": "assessment_attempts",
                    "row_id": session["attempt_id"],
                    "column_name": "proctoring_violations"
                }
            ).execute()
        
        # Update session snapshot count
        supabase_client.rpc(
            "increment",
            {
                "table_name": "proctoring_sessions",
                "row_id": session_id,
                "column_name": "total_snapshots"
            }
        ).execute()
        
        return {
            "message": "Snapshot uploaded and analyzed",
            "snapshot": snapshot,
            "analysis": analysis,
            "has_alert": snapshot_record["has_alert"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload snapshot: {str(e)}"
        )


@router.get("/sessions/{session_id}/alerts")
async def get_session_alerts(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all alerts for a proctoring session"""
    try:
        # Verify access (student or instructor of the course)
        session_result = supabase_client.table("proctoring_sessions").select(
            "id, user_id, attempt_id"
        ).eq("id", session_id).single().execute()
        
        session = session_result.data
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proctoring session not found"
            )
        
        # Allow access to own session or instructor/admin
        if session["user_id"] != current_user["id"]:
            if current_user["role"] not in ["instructor", "admin"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this session"
                )
        
        # Fetch alerts
        alerts_result = supabase_client.table("proctoring_alerts").select(
            "*, proctoring_snapshots(snapshot_url, captured_at)"
        ).eq("session_id", session_id).order("created_at", desc=True).execute()
        
        return {
            "session_id": session_id,
            "alerts": alerts_result.data,
            "total_alerts": len(alerts_result.data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch alerts: {str(e)}"
        )


@router.get("/sessions/{session_id}/review")
async def review_proctoring_session(
    session_id: str,
    current_user: dict = Depends(get_current_instructor)
):
    """Review complete proctoring session with all snapshots and alerts (Instructor/Admin only)"""
    try:
        # Fetch session details
        session_result = supabase_client.table("proctoring_sessions").select(
            "*, assessment_attempts(*, assessments(*, courses(instructor_id)))"
        ).eq("id", session_id).single().execute()
        
        session = session_result.data
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proctoring session not found"
            )
        
        # Verify instructor owns the course (unless admin)
        course_instructor_id = session.get("assessment_attempts", {}).get("assessments", {}).get("courses", {}).get("instructor_id")
        
        if current_user["role"] != "admin" and course_instructor_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to review this session"
            )
        
        # Fetch all snapshots
        snapshots_result = supabase_client.table("proctoring_snapshots").select("*").eq(
            "session_id", session_id
        ).order("captured_at").execute()
        
        # Fetch all alerts
        alerts_result = supabase_client.table("proctoring_alerts").select("*").eq(
            "session_id", session_id
        ).order("created_at").execute()
        
        # Get student info
        student_result = supabase_client.table("users").select(
            "id, full_name, email"
        ).eq("id", session["user_id"]).single().execute()
        
        return {
            "session": {
                "id": session["id"],
                "started": session["session_started"],
                "ended": session.get("session_ended"),
                "status": session["status"],
                "total_snapshots": session["total_snapshots"],
                "total_alerts": session["total_alerts"]
            },
            "student": student_result.data,
            "snapshots": snapshots_result.data,
            "alerts": alerts_result.data,
            "timeline": _build_proctoring_timeline(snapshots_result.data, alerts_result.data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review session: {str(e)}"
        )


@router.post("/sessions/{session_id}/end")
async def end_proctoring_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """End a proctoring session"""
    try:
        # Verify session belongs to current user
        session_result = supabase_client.table("proctoring_sessions").select(
            "id, user_id"
        ).eq("id", session_id).single().execute()
        
        session = session_result.data
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proctoring session not found"
            )
        
        if session["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to end this session"
            )
        
        # Update session
        update_result = supabase_client.table("proctoring_sessions").update({
            "session_ended": datetime.utcnow().isoformat(),
            "status": "completed"
        }).eq("id", session_id).execute()
        
        return {
            "message": "Proctoring session ended",
            "session": update_result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end session: {str(e)}"
        )


def _build_proctoring_timeline(snapshots: List[dict], alerts: List[dict]) -> List[dict]:
    """Build a combined timeline of snapshots and alerts"""
    timeline = []
    
    for snapshot in snapshots:
        timeline.append({
            "type": "snapshot",
            "timestamp": snapshot["captured_at"],
            "data": snapshot
        })
    
    for alert in alerts:
        timeline.append({
            "type": "alert",
            "timestamp": alert["created_at"],
            "data": alert
        })
    
    # Sort by timestamp
    timeline.sort(key=lambda x: x["timestamp"])
    
    return timeline


# ============================================================================
# REAL-TIME STREAMING ENDPOINTS (WebSocket-based live proctoring)
# ============================================================================

@router.post("/sessions/{session_id}/start-realtime", status_code=status.HTTP_200_OK)
async def start_realtime_proctoring(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Initialize real-time proctoring session with live webcam streaming"""
    try:
        # Verify session belongs to user
        session_result = supabase_client.table("proctoring_sessions").select(
            "id, user_id, assessment_id, attempt_id"
        ).eq("id", session_id).single().execute()
        
        session = session_result.data
        if not session or session["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        
        # Initialize real-time session
        result = await realtime_proctoring_manager.initialize_session(
            session_id=session_id,
            user_id=current_user["id"],
            assessment_id=session["assessment_id"],
            attempt_id=session["attempt_id"]
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting realtime proctoring: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/end-realtime", status_code=status.HTTP_200_OK)
async def end_realtime_proctoring(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """End real-time proctoring session"""
    try:
        result = await realtime_proctoring_manager.end_session(session_id, "completed")
        return result
    except Exception as e:
        logger.error(f"Error ending realtime proctoring: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/realtime-status", status_code=status.HTTP_200_OK)
async def get_realtime_status(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get current real-time session status"""
    try:
        status_data = await realtime_proctoring_manager.get_session_status(session_id)
        return status_data
    except Exception as e:
        logger.error(f"Error getting realtime status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/proctor-action", status_code=status.HTTP_200_OK)
async def send_proctor_action(
    session_id: str,
    action: str,
    reason: Optional[str] = None,
    current_user: dict = Depends(get_current_instructor)
):
    """Send proctor action (warn, escalate, terminate) to student session"""
    try:
        valid_actions = ["warn", "escalate", "terminate"]
        if action not in valid_actions:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        # Broadcast action to student
        message = {
            "type": f"proctor_{action}",
            "instructor_id": current_user["id"],
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "action_required": True
        }
        
        if action == "terminate":
            await realtime_proctoring_manager.end_session(session_id, "terminated_by_proctor")
        else:
            await realtime_proctoring_manager._broadcast_to_session(session_id, message)
        
        return {"status": "success", "action": action}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending proctor action: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/proctor/{session_id}")
async def websocket_student_proctor(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for real-time proctoring with live frame streaming
    Student sends frames, server analyzes and broadcasts alerts to proctors
    """
    await websocket.accept()
    
    try:
        # Get user from token (simplified - in production use JWT validation)
        user_id = token or "student-default"
        
        # Register WebSocket connection
        await realtime_proctoring_manager.register_websocket(session_id, user_id, websocket)
        
        while True:
            # Receive frame or commands from student
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "frame":
                # Process frame
                frame_data = message.get("frame")
                timestamp = message.get("timestamp")
                
                result = await realtime_proctoring_manager.process_frame(
                    session_id=session_id,
                    frame_data=frame_data,
                    timestamp=timestamp
                )
                
                # Send acknowledgment
                await websocket.send_text(json.dumps({
                    "type": "frame_ack",
                    "status": result.get("status"),
                    "queue_size": result.get("queue_size")
                }))
            
            elif message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
        await realtime_proctoring_manager.unregister_websocket(session_id, user_id)
    
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {str(e)}")
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/ws/proctor-dashboard/{session_id}")
async def websocket_proctor_dashboard(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for proctor dashboard
    Proctors receive real-time alerts and can send commands
    """
    await websocket.accept()
    
    try:
        instructor_id = token or "instructor-default"
        
        # Register proctor WebSocket
        await realtime_proctoring_manager.register_proctor_websocket(session_id, websocket)
        
        # Send initial status
        status_data = await realtime_proctoring_manager.get_session_status(session_id)
        await websocket.send_text(json.dumps({
            "type": "session_status",
            "data": status_data
        }))
        
        while True:
            # Receive proctor commands
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "command":
                command = message.get("command")
                
                if command in ["warn", "escalate", "terminate"]:
                    # Send to student WebSocket
                    proctor_msg = {
                        "type": f"proctor_{command}",
                        "instructor_id": instructor_id,
                        "reason": message.get("reason"),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    await realtime_proctoring_manager._broadcast_to_session(session_id, proctor_msg)
                    
                    if command == "terminate":
                        await realtime_proctoring_manager.end_session(session_id, "terminated_by_proctor")
            
            elif message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    
    except WebSocketDisconnect:
        logger.info(f"Proctor WebSocket disconnected for session {session_id}")
    
    except Exception as e:
        logger.error(f"Proctor WebSocket error for session {session_id}: {str(e)}")
        try:
            await websocket.close()
        except:
            pass