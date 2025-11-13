"""
Unified Proctoring Service - Supports both manual and real-time AI-based proctoring
"""

import asyncio
import uuid
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from app.core.supabase_client import supabase_client
from app.core.gemini_client import gemini_client
from app.models.proctoring import (
    ProctoringSession, ProctorSnapshot, ProctorAlert, ProctorViolation,
    ProctorSessionReview, AlertTypeConfig, SessionAnalyticsResponse
)
from app.utils.exceptions import AppError

logger = logging.getLogger(__name__)


class ProctoringService:
    """Comprehensive proctoring service with Gemini AI integration"""
    
    # Cache for session snapshots during analysis
    _session_snapshot_cache = {}
    
    @staticmethod
    async def create_session(
        user_id: str,
        assessment_id: str,
        attempt_id: str
    ) -> ProctoringSession:
        """
        Create a new proctoring session
        
        Args:
            user_id: User ID
            assessment_id: Assessment ID
            attempt_id: Assessment attempt ID
            
        Returns:
            Created ProctoringSession
        """
        session_id = str(uuid.uuid4())
        
        session_data = {
            "id": session_id,
            "user_id": user_id,
            "assessment_id": assessment_id,
            "attempt_id": attempt_id,
            "status": "active",
            "start_time": datetime.utcnow().isoformat(),
            "duration_seconds": 0,
            "alert_count": 0,
            "violation_count": 0,
            "integrity_score": 1.0,
            "behavior_pattern": None,
            "terminated_reason": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = supabase_client.table("proctoring_sessions").insert(session_data).execute()
        
        if not response.data:
            raise AppError("Failed to create proctoring session", 500)
        
        # Initialize cache for this session
        ProctoringService._session_snapshot_cache[session_id] = []
        
        return ProctoringSession(**session_data)
    
    @staticmethod
    async def upload_and_analyze_snapshot(
        session_id: str,
        image_data: str,
        storage_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload snapshot and analyze with Gemini AI
        
        Args:
            session_id: Proctoring session ID
            image_data: Base64 encoded image data
            storage_path: Optional Supabase storage path
            
        Returns:
            Analysis results and created alert if triggered
        """
        
        # Verify session exists
        session_response = supabase_client.table("proctoring_sessions")\
            .select("*").eq("id", session_id).single().execute()
        
        if not session_response.data:
            raise AppError("Proctoring session not found", 404)
        
        # Analyze with Gemini
        analysis = await gemini_client.analyze_proctoring_image(image_data)
        
        # Create snapshot record
        snapshot_id = str(uuid.uuid4())
        snapshot_data = {
            "id": snapshot_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "image_url": storage_path or "",
            "image_key": "",
            
            # Face detection
            "faces_detected": analysis.get("faces_detected", 1),
            "face_visible": analysis.get("analysis", {}).get("face_visible", True),
            "eye_contact": analysis.get("analysis", {}).get("eye_contact", True),
            
            # Device detection
            "phone_detected": analysis.get("analysis", {}).get("phone_detected", False),
            "external_monitor_detected": analysis.get("analysis", {}).get("external_monitor_detected", False),
            "tablet_detected": analysis.get("analysis", {}).get("tablet_detected", False),
            "other_device_detected": analysis.get("analysis", {}).get("other_device_detected", False),
            
            # Head position
            "head_tilted_away": analysis.get("analysis", {}).get("head_tilted_away", False),
            "looking_down": analysis.get("analysis", {}).get("looking_down", False),
            "looking_up": analysis.get("analysis", {}).get("looking_up", False),
            "extreme_head_angle": analysis.get("analysis", {}).get("extreme_head_angle", False),
            
            # Environment
            "bright_light_glare": analysis.get("analysis", {}).get("bright_light_glare", False),
            "dark_lighting": analysis.get("analysis", {}).get("dark_lighting", False),
            "shadows_on_face": analysis.get("analysis", {}).get("shadows_on_face", False),
            
            # Suspicious activity
            "suspicious_hand_gesture": analysis.get("analysis", {}).get("suspicious_hand_gesture", False),
            "object_in_mouth": analysis.get("analysis", {}).get("object_in_mouth", False),
            "reading_from_paper": analysis.get("analysis", {}).get("reading_from_paper", False),
            "unusual_body_position": analysis.get("analysis", {}).get("unusual_body_position", False),
            
            # Background
            "books_visible": analysis.get("analysis", {}).get("books_visible", False),
            "notes_visible": analysis.get("analysis", {}).get("notes_visible", False),
            "help_text_visible": analysis.get("analysis", {}).get("help_text_visible", False),
            "other_screens_visible": analysis.get("analysis", {}).get("other_screens_visible", False),
            
            # Analysis
            "overall_suspicion_score": analysis.get("analysis", {}).get("overall_suspicion_score", 0),
            "confidence_score": analysis.get("confidence", 0.5),
            "primary_violation": analysis.get("description", None),
            "violation_severity": analysis.get("severity", "low"),
            "recommended_action": analysis.get("analysis", {}).get("recommended_action", "allow"),
            
            "alert_triggered": False,
            "alert_type": None,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Save snapshot
        snapshot_response = supabase_client.table("proctoring_snapshots").insert(snapshot_data).execute()
        
        # Cache snapshot for session analysis
        if session_id in ProctoringService._session_snapshot_cache:
            ProctoringService._session_snapshot_cache[session_id].append(snapshot_data)
        
        # Check for violations and create alerts
        alerts_created = []
        violation_types = await ProctoringService._detect_violations(session_id, snapshot_data)
        
        for violation_type in violation_types:
            alert = await ProctoringService.create_alert(
                session_id=session_id,
                snapshot_id=snapshot_id,
                alert_type=violation_type,
                analysis_data=snapshot_data
            )
            if alert:
                alerts_created.append(alert)
                snapshot_data["alert_triggered"] = True
                snapshot_data["alert_type"] = violation_type
        
        # Update snapshot with alert info
        if alerts_created:
            supabase_client.table("proctoring_snapshots").update(
                {
                    "alert_triggered": True,
                    "alert_type": alerts_created[0]["alert_type"]
                }
            ).eq("id", snapshot_id).execute()
        
        # Update session integrity score
        await ProctoringService._update_session_integrity(session_id)
        
        return {
            "snapshot_id": snapshot_id,
            "analysis": analysis,
            "alerts_created": alerts_created,
            "violations_detected": violation_types
        }
    
    @staticmethod
    async def _detect_violations(session_id: str, snapshot: Dict) -> List[str]:
        """
        Detect violations from snapshot analysis
        
        Args:
            session_id: Session ID
            snapshot: Snapshot analysis data
            
        Returns:
            List of violation types detected
        """
        violations = []
        
        # Critical: No face detected
        if snapshot["faces_detected"] == 0:
            violations.append("no_face_detected")
        
        # Critical: Multiple faces
        elif snapshot["faces_detected"] > 1:
            violations.append("multiple_faces_detected")
        
        # High: Unauthorized devices
        if snapshot["phone_detected"] or snapshot["tablet_detected"]:
            violations.append("unauthorized_object_detected")
        
        # High: Reading from paper
        if snapshot["reading_from_paper"]:
            violations.append("reading_from_paper")
        
        # High: Other screens visible
        if snapshot["other_screens_visible"]:
            violations.append("tab_switching_detected")
        
        # Medium: Eye gaze away
        if snapshot["head_tilted_away"] or snapshot["looking_down"]:
            violations.append("eye_gaze_away")
        
        # Medium: Suspicious gesture
        if snapshot["suspicious_hand_gesture"] or snapshot["object_in_mouth"]:
            violations.append("suspicious_gesture")
        
        # Medium: Unusual position
        if snapshot["unusual_body_position"] or snapshot["extreme_head_angle"]:
            violations.append("excessive_head_movement")
        
        # Low: Lighting issues
        if snapshot["bright_light_glare"] or snapshot["dark_lighting"]:
            violations.append("lighting_change_detected")
        
        return violations
    
    @staticmethod
    async def create_alert(
        session_id: str,
        snapshot_id: str,
        alert_type: str,
        analysis_data: Dict
    ) -> Optional[ProctorAlert]:
        """
        Create proctoring alert
        
        Args:
            session_id: Session ID
            snapshot_id: Snapshot ID
            alert_type: Alert type
            analysis_data: Analysis data
            
        Returns:
            Created alert or None
        """
        
        alert_config = AlertTypeConfig.ALERT_TYPES.get(
            alert_type,
            {
                "severity": "medium",
                "description": "Unknown violation",
                "recommendation": "Manual review required"
            }
        )
        
        alert_id = str(uuid.uuid4())
        alert_data = {
            "id": alert_id,
            "session_id": session_id,
            "snapshot_id": snapshot_id,
            "alert_type": alert_type,
            "severity": alert_config.get("severity", "medium"),
            "confidence": analysis_data.get("confidence_score", 0.5),
            "description": alert_config.get("description", ""),
            "details": {
                "detection_timestamp": analysis_data.get("created_at"),
                "suspicion_score": analysis_data.get("overall_suspicion_score")
            },
            "recommendation": alert_config.get("recommendation", ""),
            "status": "unreviewed",
            "reviewed_by": None,
            "review_notes": None,
            "reviewed_at": None,
            "escalation_count": 0,
            "escalated_to": None,
            "timestamp": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        response = supabase_client.table("proctoring_alerts").insert(alert_data).execute()
        
        if response.data:
            # Update session alert count
            supabase_client.table("proctoring_sessions").update({
                "alert_count": (supabase_client.table("proctoring_sessions")
                    .select("alert_count")
                    .eq("id", session_id)
                    .single()
                    .execute()
                    .data["alert_count"] or 0) + 1
            }).eq("id", session_id).execute()
            
            # Create violation record
            await ProctoringService._create_or_update_violation(session_id, alert_type)
            
            return ProctorAlert(**alert_data)
        
        return None
    
    @staticmethod
    async def _create_or_update_violation(session_id: str, violation_type: str) -> None:
        """Create or update violation tracking"""
        
        # Check if violation exists
        existing = supabase_client.table("proctoring_violations")\
            .select("*")\
            .eq("session_id", session_id)\
            .eq("violation_type", violation_type)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        violation_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        if existing.data:
            # Update existing
            violation = existing.data[0]
            total_count = (violation.get("total_count", 0) or 0) + 1
            
            supabase_client.table("proctoring_violations").update({
                "last_occurrence": now.isoformat(),
                "total_count": total_count,
                "consecutive_count": (violation.get("consecutive_count", 0) or 0) + 1
            }).eq("id", violation["id"]).execute()
        else:
            # Create new
            violation_data = {
                "id": violation_id,
                "session_id": session_id,
                "alert_id": None,
                "violation_type": violation_type,
                "severity": AlertTypeConfig.ALERT_TYPES.get(
                    violation_type, {}
                ).get("severity", "medium"),
                "first_occurrence": now.isoformat(),
                "last_occurrence": now.isoformat(),
                "total_count": 1,
                "consecutive_count": 1,
                "escalation_flag": False,
                "instructor_action": None,
                "resolved": False,
                "resolved_at": None,
                "resolution_notes": None,
                "created_at": now.isoformat()
            }
            
            supabase_client.table("proctoring_violations").insert(violation_data).execute()
    
    @staticmethod
    async def _update_session_integrity(session_id: str) -> None:
        """Calculate and update session integrity score"""
        
        # Get all alerts and violations for session
        alerts_response = supabase_client.table("proctoring_alerts")\
            .select("severity")\
            .eq("session_id", session_id)\
            .execute()
        
        alerts = alerts_response.data or []
        
        # Calculate integrity score (1.0 = perfect, 0.0 = completely compromised)
        penalty_map = {
            "critical": 0.3,
            "high": 0.15,
            "medium": 0.05,
            "low": 0.01
        }
        
        score = 1.0
        for alert in alerts:
            penalty = penalty_map.get(alert.get("severity", "medium"), 0.05)
            score -= penalty
        
        # Ensure score stays in 0-1 range
        score = max(0.0, min(1.0, score))
        
        # Update session
        supabase_client.table("proctoring_sessions").update({
            "integrity_score": score
        }).eq("id", session_id).execute()
    
    @staticmethod
    async def end_session(session_id: str, terminated: bool = False, reason: Optional[str] = None) -> ProctoringSession:
        """
        End a proctoring session
        
        Args:
            session_id: Session ID
            terminated: Whether session was terminated early
            reason: Termination reason if applicable
            
        Returns:
            Updated session
        """
        
        session_response = supabase_client.table("proctoring_sessions")\
            .select("*").eq("id", session_id).single().execute()
        
        if not session_response.data:
            raise AppError("Proctoring session not found", 404)
        
        session = session_response.data
        start_time = datetime.fromisoformat(session["start_time"])
        duration = int((datetime.utcnow() - start_time).total_seconds())
        
        # Analyze session behavior
        session_snapshots = ProctoringService._session_snapshot_cache.get(session_id, [])
        behavior_analysis = await gemini_client.analyze_session_behavior(session_snapshots)
        
        update_data = {
            "status": "terminated" if terminated else "completed",
            "end_time": datetime.utcnow().isoformat(),
            "duration_seconds": duration,
            "terminated_reason": reason,
            "behavior_pattern": behavior_analysis.get("pattern", "unknown"),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = supabase_client.table("proctoring_sessions").update(update_data).eq("id", session_id).execute()
        
        # Clear cache
        if session_id in ProctoringService._session_snapshot_cache:
            del ProctoringService._session_snapshot_cache[session_id]
        
        if response.data:
            return ProctoringSession(**{**session, **update_data})
        
        raise AppError("Failed to end proctoring session", 500)
    
    @staticmethod
    async def get_session_alerts(session_id: str) -> List[ProctorAlert]:
        """Get all alerts for a session"""
        
        response = supabase_client.table("proctoring_alerts")\
            .select("*")\
            .eq("session_id", session_id)\
            .order("timestamp", desc=False)\
            .execute()
        
        return [ProctorAlert(**alert) for alert in (response.data or [])]
    
    @staticmethod
    async def review_session(
        session_id: str,
        instructor_id: str,
        integrity_verdict: str,
        notes: Optional[str] = None,
        requires_escalation: bool = False
    ) -> Dict[str, Any]:
        """
        Instructor reviews proctoring session
        
        Args:
            session_id: Session ID
            instructor_id: Instructor user ID
            integrity_verdict: "pass", "marginal_pass", or "fail"
            notes: Review notes
            requires_escalation: Whether to escalate
            
        Returns:
            Review summary
        """
        
        # Get session
        session_response = supabase_client.table("proctoring_sessions")\
            .select("*").eq("id", session_id).single().execute()
        
        if not session_response.data:
            raise AppError("Proctoring session not found", 404)
        
        # Get all alerts
        alerts_response = supabase_client.table("proctoring_alerts")\
            .select("*")\
            .eq("session_id", session_id)\
            .execute()
        
        alerts = alerts_response.data or []
        
        # Build review
        review_data = {
            "session_id": session_id,
            "review_status": "escalated" if requires_escalation else "reviewed",
            "total_alerts": len(alerts),
            "critical_alerts": sum(1 for a in alerts if a.get("severity") == "critical"),
            "high_alerts": sum(1 for a in alerts if a.get("severity") == "high"),
            "medium_alerts": sum(1 for a in alerts if a.get("severity") == "medium"),
            "low_alerts": sum(1 for a in alerts if a.get("severity") == "low"),
            "integrity_verdict": integrity_verdict,
            "integrity_confidence": session_response.data.get("integrity_score", 1.0),
            "instructor_notes": notes,
            "requires_escalation": requires_escalation,
            "reviewed_by": instructor_id,
            "reviewed_at": datetime.utcnow().isoformat()
        }
        
        # Mark alerts as reviewed
        for alert in alerts:
            supabase_client.table("proctoring_alerts").update({
                "status": "reviewed",
                "reviewed_by": instructor_id,
                "reviewed_at": datetime.utcnow().isoformat()
            }).eq("id", alert["id"]).execute()
        
        return review_data
    
    @staticmethod
    async def get_session_analytics(session_id: str) -> SessionAnalyticsResponse:
        """Get comprehensive session analytics"""
        
        # Get session
        session_response = supabase_client.table("proctoring_sessions")\
            .select("*").eq("id", session_id).single().execute()
        
        if not session_response.data:
            raise AppError("Proctoring session not found", 404)
        
        session = session_response.data
        
        # Get alerts and violations
        alerts_response = supabase_client.table("proctoring_alerts")\
            .select("*")\
            .eq("session_id", session_id)\
            .execute()
        
        violations_response = supabase_client.table("proctoring_violations")\
            .select("*")\
            .eq("session_id", session_id)\
            .execute()
        
        alerts = alerts_response.data or []
        violations = violations_response.data or []
        
        # Build statistics
        alerts_by_type = {}
        alerts_by_severity = {}
        
        for alert in alerts:
            alert_type = alert.get("alert_type", "unknown")
            severity = alert.get("severity", "medium")
            
            alerts_by_type[alert_type] = alerts_by_type.get(alert_type, 0) + 1
            alerts_by_severity[severity] = alerts_by_severity.get(severity, 0) + 1
        
        violations_by_type = {}
        for violation in violations:
            v_type = violation.get("violation_type", "unknown")
            violations_by_type[v_type] = violations_by_type.get(v_type, 0) + 1
        
        # Calculate scores
        behavior_score = 1.0 - (len(alerts) * 0.05)
        compliance_score = max(0, session.get("integrity_score", 1.0))
        
        return SessionAnalyticsResponse(
            session_id=session_id,
            user_id=session.get("user_id"),
            assessment_id=session.get("assessment_id"),
            duration_minutes=int(session.get("duration_seconds", 0) / 60),
            total_snapshots=0,  # Would need to query separately
            total_alerts=len(alerts),
            total_violations=len(violations),
            alerts_by_type=alerts_by_type,
            alerts_by_severity=alerts_by_severity,
            violations_by_type=violations_by_type,
            integrity_score=session.get("integrity_score", 1.0),
            behavior_score=max(0, behavior_score),
            compliance_score=compliance_score,
            session_status=session.get("status"),
            integrity_verdict="pass" if compliance_score > 0.7 else "fail",
            recommendations=ProctoringService._get_recommendations(alerts, violations),
            flagged_for_review=len(alerts) > 5 or any(a.get("severity") == "critical" for a in alerts)
        )
    
    @staticmethod
    def _get_recommendations(alerts: List[Dict], violations: List[Dict]) -> List[str]:
        """Generate recommendations based on alerts and violations"""
        
        recommendations = []
        
        critical_count = sum(1 for a in alerts if a.get("severity") == "critical")
        if critical_count > 0:
            recommendations.append("CRITICAL VIOLATIONS DETECTED - Immediate escalation required")
        
        no_face_alerts = sum(1 for a in alerts if a.get("alert_type") == "no_face_detected")
        if no_face_alerts > 0:
            recommendations.append("Face not visible in frames - Identity verification required")
        
        multiple_faces = sum(1 for a in alerts if a.get("alert_type") == "multiple_faces_detected")
        if multiple_faces > 0:
            recommendations.append("Multiple persons detected - Session integrity compromised")
        
        device_alerts = sum(1 for a in alerts if a.get("alert_type") == "unauthorized_object_detected")
        if device_alerts > 0:
            recommendations.append("Unauthorized devices detected - Request device removal")
        
        if len(alerts) > 10:
            recommendations.append("Excessive alerts - Manual review recommended")
        
        if not recommendations:
            recommendations.append("No significant issues detected - Session appears valid")
        
        return recommendations


# ============================================================================
# REAL-TIME STREAMING PROCTORING (WebSocket-based live monitoring)
# ============================================================================

class RealtimeProctoringManager:
    """Manages real-time proctoring sessions with live frame capture and WebSocket streaming"""
    
    def __init__(self):
        """Initialize the real-time proctoring manager"""
        self.active_sessions: Dict[str, Dict] = {}
        self.frame_queues: Dict[str, asyncio.Queue] = {}
        self.websocket_connections: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.analysis_tasks: Dict[str, asyncio.Task] = {}
        self.session_alerts_cache: Dict[str, list] = defaultdict(list)
        self.proctor_connections: Dict[str, list] = defaultdict(list)
        
        self.capture_interval = 5
        self.max_queue_size = 20
        self.violation_thresholds = {
            "critical_alerts_threshold": 5,
            "hourly_alert_rate": 12,
            "consecutive_violations": 3
        }
    
    async def initialize_session(
        self,
        session_id: str,
        user_id: str,
        assessment_id: str,
        attempt_id: str
    ) -> Dict[str, Any]:
        """Initialize real-time proctoring session with live frame streaming"""
        
        session_data = {
            "id": session_id,
            "user_id": user_id,
            "assessment_id": assessment_id,
            "attempt_id": attempt_id,
            "status": "active",
            "start_time": datetime.utcnow().isoformat(),
            "frames_captured": 0,
            "alerts_generated": 0,
            "violations_detected": 0,
            "integrity_score": 1.0,
            "is_live": True,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            response = supabase_client.table("proctoring_sessions").insert(session_data).execute()
            
            if response.data:
                self.active_sessions[session_id] = session_data
                self.frame_queues[session_id] = asyncio.Queue(maxsize=self.max_queue_size)
                self.analysis_tasks[session_id] = asyncio.create_task(
                    self._frame_analysis_loop(session_id)
                )
                
                logger.info(f"Real-time proctoring session initialized: {session_id}")
                return {
                    "session_id": session_id,
                    "status": "initialized",
                    "message": "Live proctoring session started. Webcam monitoring active.",
                    "capture_interval": self.capture_interval
                }
        except Exception as e:
            logger.error(f"Failed to initialize session {session_id}: {str(e)}")
            raise
    
    async def process_frame(
        self,
        session_id: str,
        frame_data: str,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process webcam frame from student"""
        
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        try:
            if self.frame_queues[session_id].full():
                try:
                    self.frame_queues[session_id].get_nowait()
                except asyncio.QueueEmpty:
                    pass
            
            await self.frame_queues[session_id].put({
                "frame": frame_data,
                "timestamp": timestamp or datetime.utcnow().isoformat(),
                "frame_id": str(uuid.uuid4())
            })
            
            session = self.active_sessions[session_id]
            session["frames_captured"] = session.get("frames_captured", 0) + 1
            
            return {
                "status": "received",
                "frame_id": session["frames_captured"],
                "queue_size": self.frame_queues[session_id].qsize()
            }
        except Exception as e:
            logger.error(f"Error processing frame for session {session_id}: {str(e)}")
            return {"error": str(e)}
    
    async def _frame_analysis_loop(self, session_id: str) -> None:
        """Background async task that analyzes frames and detects violations"""
        
        violation_streak = 0
        
        try:
            while session_id in self.active_sessions and self.active_sessions[session_id]["status"] == "active":
                try:
                    frame_data = await asyncio.wait_for(
                        self.frame_queues[session_id].get(),
                        timeout=30.0
                    )
                    
                    frame_id = frame_data["frame_id"]
                    timestamp = frame_data["timestamp"]
                    image_base64 = frame_data["frame"]
                    
                    # Analyze with Gemini AI
                    analysis = await gemini_client.analyze_proctoring_image(image_base64)
                    
                    # Save snapshot
                    snapshot = await self._save_snapshot(
                        session_id=session_id,
                        frame_id=frame_id,
                        timestamp=timestamp,
                        analysis=analysis
                    )
                    
                    # Detect violations
                    violations = self._detect_violations_from_analysis(analysis)
                    
                    # Create alerts
                    alerts = []
                    for violation in violations:
                        alert = await self._create_violation_alert(
                            session_id=session_id,
                            snapshot_id=snapshot.get("id"),
                            violation=violation,
                            analysis=analysis
                        )
                        if alert:
                            alerts.append(alert)
                    
                    if violations:
                        violation_streak += 1
                    else:
                        violation_streak = 0
                    
                    # Check escalation
                    session_data = self.active_sessions[session_id]
                    alert_count = session_data.get("alerts_generated", 0)
                    
                    should_escalate = await self._check_escalation_conditions(
                        session_id=session_id,
                        violation_streak=violation_streak,
                        alert_count=alert_count + len(alerts),
                        current_violations=violations
                    )
                    
                    if should_escalate:
                        await self._escalate_session(session_id, should_escalate)
                    
                    # Broadcast alerts
                    if alerts:
                        await self._broadcast_alerts_to_proctors(session_id, alerts)
                    
                    # Send status update
                    await self._send_status_update_to_student(session_id, {
                        "frame_processed": True,
                        "violations_detected": len(violations),
                        "alerts": len(alerts),
                        "integrity_score": session_data.get("integrity_score")
                    })
                    
                    # Update session
                    session_data["alerts_generated"] = session_data.get("alerts_generated", 0) + len(alerts)
                    session_data["violations_detected"] = session_data.get("violations_detected", 0) + len(violations)
                    
                except asyncio.TimeoutError:
                    await self._send_timeout_warning(session_id)
                except Exception as e:
                    logger.error(f"Error in frame analysis loop for {session_id}: {str(e)}")
                    await asyncio.sleep(1)
        
        finally:
            logger.info(f"Frame analysis loop ended for session {session_id}")
    
    async def _save_snapshot(
        self,
        session_id: str,
        frame_id: str,
        timestamp: str,
        analysis: Dict
    ) -> Dict:
        """Save snapshot record to database"""
        
        snapshot_data = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "frame_id": frame_id,
            "timestamp": timestamp,
            "image_url": "",
            "image_key": "",
            "faces_detected": analysis.get("faces_detected", 1),
            "face_visible": analysis.get("analysis", {}).get("face_visible", True),
            "eye_contact": analysis.get("analysis", {}).get("eye_contact", True),
            "phone_detected": analysis.get("analysis", {}).get("phone_detected", False),
            "external_monitor_detected": analysis.get("analysis", {}).get("external_monitor_detected", False),
            "tablet_detected": analysis.get("analysis", {}).get("tablet_detected", False),
            "other_device_detected": analysis.get("analysis", {}).get("other_device_detected", False),
            "head_tilted_away": analysis.get("analysis", {}).get("head_tilted_away", False),
            "looking_down": analysis.get("analysis", {}).get("looking_down", False),
            "looking_up": analysis.get("analysis", {}).get("looking_up", False),
            "extreme_head_angle": analysis.get("analysis", {}).get("extreme_head_angle", False),
            "bright_light_glare": analysis.get("analysis", {}).get("bright_light_glare", False),
            "dark_lighting": analysis.get("analysis", {}).get("dark_lighting", False),
            "shadows_on_face": analysis.get("analysis", {}).get("shadows_on_face", False),
            "suspicious_hand_gesture": analysis.get("analysis", {}).get("suspicious_hand_gesture", False),
            "object_in_mouth": analysis.get("analysis", {}).get("object_in_mouth", False),
            "reading_from_paper": analysis.get("analysis", {}).get("reading_from_paper", False),
            "unusual_body_position": analysis.get("analysis", {}).get("unusual_body_position", False),
            "books_visible": analysis.get("analysis", {}).get("books_visible", False),
            "notes_visible": analysis.get("analysis", {}).get("notes_visible", False),
            "help_text_visible": analysis.get("analysis", {}).get("help_text_visible", False),
            "other_screens_visible": analysis.get("analysis", {}).get("other_screens_visible", False),
            "overall_suspicion_score": analysis.get("analysis", {}).get("overall_suspicion_score", 0),
            "confidence_score": analysis.get("confidence", 0.5),
            "primary_violation": analysis.get("description", None),
            "violation_severity": analysis.get("severity", "low"),
            "recommended_action": analysis.get("analysis", {}).get("recommended_action", "allow"),
            "alert_triggered": False,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            response = supabase_client.table("proctoring_snapshots").insert(snapshot_data).execute()
            return response.data[0] if response.data else snapshot_data
        except Exception as e:
            logger.error(f"Failed to save snapshot: {str(e)}")
            return snapshot_data
    
    def _detect_violations_from_analysis(self, analysis: Dict) -> list:
        """Detect violations from Gemini AI analysis"""
        
        violations = []
        
        if analysis.get("faces_detected", 0) == 0:
            violations.append("no_face_detected")
        elif analysis.get("faces_detected", 0) > 1:
            violations.append("multiple_faces_detected")
        
        if (analysis.get("analysis", {}).get("phone_detected") or 
            analysis.get("analysis", {}).get("tablet_detected")):
            violations.append("unauthorized_object_detected")
        
        if analysis.get("analysis", {}).get("reading_from_paper"):
            violations.append("reading_from_paper")
        
        if analysis.get("analysis", {}).get("other_screens_visible"):
            violations.append("tab_switching_detected")
        
        if (analysis.get("analysis", {}).get("head_tilted_away") or 
            analysis.get("analysis", {}).get("looking_down")):
            violations.append("eye_gaze_away")
        
        if (analysis.get("analysis", {}).get("suspicious_hand_gesture") or 
            analysis.get("analysis", {}).get("object_in_mouth")):
            violations.append("suspicious_gesture")
        
        if (analysis.get("analysis", {}).get("unusual_body_position") or 
            analysis.get("analysis", {}).get("extreme_head_angle")):
            violations.append("excessive_head_movement")
        
        return violations
    
    async def _create_violation_alert(
        self,
        session_id: str,
        snapshot_id: str,
        violation: str,
        analysis: Dict
    ) -> Optional[Dict]:
        """Create alert for violation"""
        
        alert_config = AlertTypeConfig.ALERT_TYPES.get(violation, {})
        
        alert_data = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "snapshot_id": snapshot_id,
            "alert_type": violation,
            "severity": alert_config.get("severity", "medium"),
            "confidence": analysis.get("confidence", 0.5),
            "description": alert_config.get("description", ""),
            "details": {"analysis_timestamp": datetime.utcnow().isoformat()},
            "recommendation": alert_config.get("recommendation", ""),
            "status": "unreviewed",
            "timestamp": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            response = supabase_client.table("proctoring_alerts").insert(alert_data).execute()
            self.session_alerts_cache[session_id].append(alert_data)
            return alert_data if response.data else None
        except Exception as e:
            logger.error(f"Failed to create alert: {str(e)}")
            return None
    
    async def _check_escalation_conditions(
        self,
        session_id: str,
        violation_streak: int,
        alert_count: int,
        current_violations: list
    ) -> Optional[str]:
        """Check if session should be escalated"""
        
        critical_violations = ["no_face_detected", "multiple_faces_detected"]
        if any(v in critical_violations for v in current_violations):
            return "critical_violation_detected"
        
        if alert_count > self.violation_thresholds["critical_alerts_threshold"]:
            return "excessive_alerts"
        
        if violation_streak > self.violation_thresholds["consecutive_violations"]:
            return "consecutive_violations"
        
        return None
    
    async def _escalate_session(self, session_id: str, reason: str) -> None:
        """Escalate session to proctors"""
        
        session = self.active_sessions[session_id]
        session["escalation_reason"] = reason
        session["escalated_at"] = datetime.utcnow().isoformat()
        
        logger.warning(f"Session {session_id} escalated: {reason}")
        
        await self._broadcast_to_proctors(session_id, {
            "type": "escalation_alert",
            "session_id": session_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "action_required": True
        })
        
        if reason == "critical_violation_detected":
            await self._send_termination_warning(session_id)
    
    async def _broadcast_alerts_to_proctors(self, session_id: str, alerts: list) -> None:
        """Broadcast alerts to proctors in real-time"""
        
        message = {
            "type": "live_alert",
            "session_id": session_id,
            "alerts": alerts,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._broadcast_to_proctors(session_id, message)
    
    async def _send_status_update_to_student(self, session_id: str, status: Dict) -> None:
        """Send status update to student's WebSocket client"""
        
        if session_id not in self.websocket_connections:
            return
        
        message = {
            "type": "status_update",
            "session_id": session_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._broadcast_to_session(session_id, message)
    
    async def _send_timeout_warning(self, session_id: str) -> None:
        """Send warning if no frames received for 30 seconds"""
        
        message = {
            "type": "warning",
            "session_id": session_id,
            "message": "No webcam input detected for 30 seconds. Please ensure camera is working.",
            "action": "check_camera",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._broadcast_to_session(session_id, message)
    
    async def _send_termination_warning(self, session_id: str) -> None:
        """Send termination warning for critical violations"""
        
        message = {
            "type": "critical_warning",
            "session_id": session_id,
            "message": "Critical proctoring violations detected. Exam will be terminated in 30 seconds.",
            "severity": "critical",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._broadcast_to_session(session_id, message)
    
    async def _broadcast_to_session(self, session_id: str, message: Dict) -> None:
        """Broadcast to all connections in session"""
        
        if session_id not in self.websocket_connections:
            return
        
        message_str = json.dumps(message)
        for websocket in list(self.websocket_connections[session_id].values()):
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                logger.error(f"Failed to send message: {str(e)}")
    
    async def _broadcast_to_proctors(self, session_id: str, message: Dict) -> None:
        """Broadcast to all proctors monitoring session"""
        
        if session_id not in self.proctor_connections:
            return
        
        message_str = json.dumps(message)
        for websocket in self.proctor_connections[session_id]:
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                logger.error(f"Failed to send to proctor: {str(e)}")
    
    async def end_session(self, session_id: str, reason: str = "completed") -> Dict:
        """End real-time proctoring session"""
        
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        if session_id in self.analysis_tasks:
            self.analysis_tasks[session_id].cancel()
            try:
                await self.analysis_tasks[session_id]
            except asyncio.CancelledError:
                pass
            del self.analysis_tasks[session_id]
        
        session["status"] = reason
        session["end_time"] = datetime.utcnow().isoformat()
        
        try:
            supabase_client.table("proctoring_sessions").update({
                "status": reason,
                "end_time": session["end_time"]
            }).eq("id", session_id).execute()
        except Exception as e:
            logger.error(f"Failed to update session in database: {str(e)}")
        
        await self._broadcast_to_session(session_id, {
            "type": "session_ended",
            "session_id": session_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Cleanup
        del self.active_sessions[session_id]
        if session_id in self.frame_queues:
            del self.frame_queues[session_id]
        if session_id in self.websocket_connections:
            del self.websocket_connections[session_id]
        if session_id in self.proctor_connections:
            del self.proctor_connections[session_id]
        if session_id in self.session_alerts_cache:
            del self.session_alerts_cache[session_id]
        
        return {
            "session_id": session_id,
            "status": "ended",
            "reason": reason,
            "frames_processed": session.get("frames_captured", 0),
            "alerts_generated": session.get("alerts_generated", 0)
        }
    
    async def register_websocket(
        self,
        session_id: str,
        user_id: str,
        websocket: Any
    ) -> None:
        """Register WebSocket connection for real-time communication"""
        self.websocket_connections[session_id][user_id] = websocket
        logger.info(f"WebSocket registered for session {session_id}, user {user_id}")
    
    async def unregister_websocket(self, session_id: str, user_id: str) -> None:
        """Unregister WebSocket connection"""
        if session_id in self.websocket_connections:
            self.websocket_connections[session_id].pop(user_id, None)
        logger.info(f"WebSocket unregistered for session {session_id}, user {user_id}")
    
    async def register_proctor_websocket(self, session_id: str, websocket: Any) -> None:
        """Register proctor WebSocket for live monitoring"""
        self.proctor_connections[session_id].append(websocket)
        logger.info(f"Proctor WebSocket registered for session {session_id}")
    
    async def get_session_status(self, session_id: str) -> Dict:
        """Get current session status and recent alerts"""
        
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "status": session.get("status"),
            "frames_captured": session.get("frames_captured", 0),
            "alerts_generated": session.get("alerts_generated", 0),
            "violations_detected": session.get("violations_detected", 0),
            "integrity_score": session.get("integrity_score", 1.0),
            "recent_alerts": self.session_alerts_cache[session_id][-5:] if session_id in self.session_alerts_cache else []
        }


# Global singleton instance
realtime_proctoring_manager = RealtimeProctoringManager()


