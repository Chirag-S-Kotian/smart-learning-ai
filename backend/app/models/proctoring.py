from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ProctoringSession(BaseModel):
    """Proctoring session model"""
    id: str
    user_id: str
    assessment_id: str
    attempt_id: str
    status: str  # "active", "completed", "terminated", "flagged"
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: int = 0
    alert_count: int = 0
    violation_count: int = 0
    integrity_score: float = Field(default=1.0, ge=0, le=1)  # 0-1, higher is better
    behavior_pattern: Optional[str] = None  # "normal_behavior", "highly_suspicious", etc.
    terminated_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProctorSnapshot(BaseModel):
    """Individual proctoring snapshot/frame capture"""
    id: str
    session_id: str
    timestamp: datetime
    image_url: str  # URL in Supabase storage
    image_key: str  # Storage key path
    
    # Face detection results
    faces_detected: int  # 0, 1, 2+
    face_visible: bool
    eye_contact: bool
    
    # Detection results
    phone_detected: bool
    external_monitor_detected: bool
    tablet_detected: bool
    other_device_detected: bool
    
    # Head position
    head_tilted_away: bool
    looking_down: bool
    looking_up: bool
    extreme_head_angle: bool
    
    # Environment
    bright_light_glare: bool
    dark_lighting: bool
    shadows_on_face: bool
    
    # Suspicious activity
    suspicious_hand_gesture: bool
    object_in_mouth: bool
    reading_from_paper: bool
    unusual_body_position: bool
    
    # Background analysis
    books_visible: bool
    notes_visible: bool
    help_text_visible: bool
    other_screens_visible: bool
    
    # Analysis results
    overall_suspicion_score: float = Field(default=0.0, ge=0, le=1)
    confidence_score: float = Field(default=0.5, ge=0, le=1)
    primary_violation: Optional[str] = None
    violation_severity: str = "low"  # low, medium, high, critical
    recommended_action: str = "allow"  # allow, warn, flag_for_review, terminate
    
    # Metadata
    alert_triggered: bool = False
    alert_type: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProctorAlert(BaseModel):
    """Proctoring alert/violation alert"""
    id: str
    session_id: str
    snapshot_id: Optional[str] = None
    
    # Alert classification
    alert_type: str  # See ALERT_TYPES
    severity: str  # low, medium, high, critical
    confidence: float = Field(default=0.5, ge=0, le=1)
    
    # Details
    description: str
    details: dict = {}  # Additional context
    recommendation: str
    
    # Status tracking
    status: str = "unreviewed"  # unreviewed, reviewed, dismissed, escalated
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    
    # Escalation
    escalation_count: int = 0
    escalated_to: Optional[str] = None
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProctorViolation(BaseModel):
    """Tracked violation over session"""
    id: str
    session_id: str
    alert_id: Optional[str] = None
    
    # Violation info
    violation_type: str
    severity: str  # low, medium, high, critical
    
    # Occurrence tracking
    first_occurrence: datetime
    last_occurrence: datetime
    total_count: int = 1
    consecutive_count: int = 1  # How many in a row
    
    # Impact
    escalation_flag: bool = False
    instructor_action: Optional[str] = None
    
    # Resolution
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProctorSessionReview(BaseModel):
    """Instructor review of proctoring session"""
    session_id: str
    review_status: str  # "pending", "reviewed", "escalated", "cleared"
    
    # Summary
    total_alerts: int = 0
    critical_alerts: int = 0
    high_alerts: int = 0
    medium_alerts: int = 0
    low_alerts: int = 0
    
    # Violations
    total_violations: int = 0
    unique_violation_types: List[str] = []
    
    # Decision
    integrity_verdict: str = "pass"  # pass, marginal_pass, fail
    integrity_confidence: float = Field(default=1.0, ge=0, le=1)
    
    # Notes
    instructor_notes: Optional[str] = None
    recommended_action: Optional[str] = None  # allow, retake, escalate
    
    # Admin escalation
    requires_escalation: bool = False
    escalation_reason: Optional[str] = None
    
    # Timeline reference
    timeline_url: Optional[str] = None
    
    reviewed_by: str
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)


class ProctorSessionTimeline(BaseModel):
    """Combined timeline for visualization"""
    session_id: str
    events: List[dict] = []  # List of events (alerts + snapshots)
    total_events: int = 0
    alert_distribution: dict = {}  # Alert types count
    violation_timeline: List[dict] = []  # Timeline of violations
    behavior_trends: dict = {}  # Trend analysis


# Alert type constants and configuration
class AlertTypeConfig:
    """Configuration for different alert types"""
    
    ALERT_TYPES = {
        "no_face_detected": {
            "severity": "critical",
            "description": "Test-taker's face not visible in frame",
            "recommendation": "Terminate exam - cannot verify test-taker identity"
        },
        "multiple_faces_detected": {
            "severity": "critical",
            "description": "Multiple people detected in view",
            "recommendation": "Terminate exam immediately"
        },
        "excessive_head_movement": {
            "severity": "high",
            "description": "Excessive head turning or unusual head angles",
            "recommendation": "Send warning, increase monitoring frequency"
        },
        "eye_gaze_away": {
            "severity": "medium",
            "description": "Test-taker looking away from screen",
            "recommendation": "Continue monitoring with increased frequency"
        },
        "unauthorized_object_detected": {
            "severity": "high",
            "description": "Phone, tablet, or other unauthorized device visible",
            "recommendation": "Send warning, request removal of device"
        },
        "environmental_change": {
            "severity": "medium",
            "description": "Significant changes in background or lighting",
            "recommendation": "Request environment stabilization"
        },
        "audio_anomaly": {
            "severity": "high",
            "description": "Foreign voices or unusual sounds detected",
            "recommendation": "Send warning, verify test-taker is alone"
        },
        "tab_switching_detected": {
            "severity": "medium",
            "description": "Multiple browser tabs or window switching detected",
            "recommendation": "Send warning, remind of single-tab policy"
        },
        "suspicious_gesture": {
            "severity": "medium",
            "description": "Hand gestures or suspicious movement detected",
            "recommendation": "Increase monitoring frequency"
        },
        "timeout_no_movement": {
            "severity": "medium",
            "description": "No movement detected for extended period",
            "recommendation": "Send ping to verify test-taker presence"
        },
        "lighting_change_detected": {
            "severity": "low",
            "description": "Lighting conditions changed significantly",
            "recommendation": "Monitor for intentional obstruction"
        },
        "posture_anomaly": {
            "severity": "medium",
            "description": "Unusual posture or slouching detected",
            "recommendation": "Send reminder to maintain proper posture"
        },
        "reading_from_paper": {
            "severity": "high",
            "description": "Test-taker appears to be reading from unauthorized materials",
            "recommendation": "Send warning, request desk verification"
        }
    }
    
    SEVERITY_LEVELS = ["low", "medium", "high", "critical"]
    
    VIOLATION_ACTIONS = {
        "critical": "terminate_immediately",
        "high": "send_warning_and_flag",
        "medium": "continue_monitoring",
        "low": "monitor_passively"
    }


class SessionAnalyticsResponse(BaseModel):
    """Response for session analytics"""
    session_id: str
    user_id: str
    assessment_id: str
    
    # Summary
    duration_minutes: int
    total_snapshots: int
    total_alerts: int
    total_violations: int
    
    # Breakdown
    alerts_by_type: dict
    alerts_by_severity: dict
    violations_by_type: dict
    
    # Scores
    integrity_score: float
    behavior_score: float
    compliance_score: float
    
    # Status
    session_status: str
    integrity_verdict: str
    
    # Recommendations
    recommendations: List[str]
    flagged_for_review: bool


