"""
Advanced Proctoring Features
- Eye Tracking: Monitors eye gaze direction and fixation points
- Noise Detection: Detects ambient noise and speech patterns
- Face Recognition: Verifies student identity and detects spoofing attempts
"""

import uuid
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
import json

from app.core.supabase_client import supabase_client
from app.core.gemini_client import gemini_client
from app.utils.exceptions import AppError

logger = logging.getLogger(__name__)


# ============================================================================
# EYE TRACKING SERVICE
# ============================================================================

class EyeTrackingService:
    """
    Advanced eye tracking service for proctoring
    - Monitors eye gaze direction
    - Detects off-screen looking patterns
    - Tracks fixation points and duration
    - Identifies suspicious eye movement patterns
    """
    
    @staticmethod
    async def analyze_eye_gaze(
        session_id: str,
        frame_data: str,
        screen_resolution: Tuple[int, int] = (1920, 1080)
    ) -> Dict[str, Any]:
        """
        Analyze eye gaze from frame
        
        Args:
            session_id: Proctoring session ID
            frame_data: Base64 encoded frame
            screen_resolution: Screen resolution tuple (width, height)
            
        Returns:
            Eye tracking analysis results
        """
        
        try:
            # Use Gemini to analyze eye position and gaze direction
            analysis = await gemini_client.analyze_eye_tracking(frame_data)
            
            gaze_data = {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                
                # Eye detection
                "left_eye_detected": analysis.get("left_eye_detected", False),
                "right_eye_detected": analysis.get("right_eye_detected", False),
                "both_eyes_visible": analysis.get("both_eyes_visible", False),
                
                # Gaze direction (normalized 0-1)
                "gaze_point_x": analysis.get("gaze_point_x", 0.5),
                "gaze_point_y": analysis.get("gaze_point_y", 0.5),
                "gaze_on_screen": analysis.get("gaze_on_screen", True),
                "gaze_confidence": analysis.get("gaze_confidence", 0.0),
                
                # Eye state
                "eyes_open": analysis.get("eyes_open", True),
                "blinking_rate": analysis.get("blinking_rate", 0.0),  # blinks per minute
                "eye_closure_duration_ms": analysis.get("eye_closure_duration", 0),
                "prolonged_blink": analysis.get("prolonged_blink", False),
                
                # Head position relative to gaze
                "head_pose_yaw": analysis.get("head_pose_yaw", 0.0),  # degrees -45 to 45
                "head_pose_pitch": analysis.get("head_pose_pitch", 0.0),  # degrees -45 to 45
                "head_pose_roll": analysis.get("head_pose_roll", 0.0),  # degrees -45 to 45
                
                # Pupil metrics
                "pupil_diameter_left": analysis.get("pupil_diameter_left", 0.0),
                "pupil_diameter_right": analysis.get("pupil_diameter_right", 0.0),
                "pupil_size_difference": analysis.get("pupil_size_difference", 0.0),
                
                # Fixation analysis
                "fixation_duration_ms": analysis.get("fixation_duration", 0),
                "fixation_point_x": analysis.get("fixation_point_x", 0.5),
                "fixation_point_y": analysis.get("fixation_point_y", 0.5),
                "number_of_fixations": analysis.get("num_fixations", 0),
                "average_fixation_duration_ms": analysis.get("avg_fixation_duration", 0),
                
                # Gaze patterns
                "saccade_speed": analysis.get("saccade_speed", 0.0),  # degrees per second
                "gaze_stability": analysis.get("gaze_stability", 1.0),  # 0-1, higher = more stable
                "smooth_pursuit_detected": analysis.get("smooth_pursuit", False),
                
                # Suspicious patterns
                "gaze_away_from_screen": analysis.get("gaze_away", False),
                "repeated_off_screen_glances": analysis.get("repeated_glances", False),
                "gaze_at_keyboard": analysis.get("gaze_at_keyboard", False),
                "gaze_at_external_object": analysis.get("gaze_at_object", False),
                
                # Risk indicators
                "eye_fatigue_indicator": analysis.get("eye_fatigue", False),
                "suspicious_eye_pattern": analysis.get("suspicious_pattern", False),
                "potential_cheating_sign": analysis.get("potential_cheating", False),
                
                # Confidence scores
                "overall_confidence": analysis.get("overall_confidence", 0.5),
                "violation_probability": analysis.get("violation_prob", 0.0),
                
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Save to database
            response = supabase_client.table("eye_tracking_data").insert(gaze_data).execute()
            
            if response.data:
                logger.info(f"Eye tracking data saved for session {session_id}")
            
            return {
                "success": True,
                "tracking_id": gaze_data["id"],
                "gaze_on_screen": gaze_data["gaze_on_screen"],
                "suspension_flags": await EyeTrackingService._check_suspension_flags(gaze_data),
                "risk_level": EyeTrackingService._calculate_risk_level(gaze_data)
            }
            
        except Exception as e:
            logger.error(f"Eye tracking analysis failed: {str(e)}")
            raise AppError(f"Eye tracking analysis failed: {str(e)}", 500)
    
    @staticmethod
    async def _check_suspension_flags(gaze_data: Dict) -> List[str]:
        """Check for suspicious eye tracking patterns"""
        
        flags = []
        
        if gaze_data["gaze_away_from_screen"]:
            flags.append("gaze_off_screen")
        
        if gaze_data["repeated_off_screen_glances"]:
            flags.append("repeated_glances_detected")
        
        if gaze_data["gaze_at_keyboard"]:
            flags.append("suspicious_gaze_pattern")
        
        if gaze_data["prolonged_blink"]:
            flags.append("prolonged_eye_closure")
        
        if gaze_data["eye_fatigue_indicator"]:
            flags.append("potential_eye_fatigue")
        
        if gaze_data["gaze_stability"] < 0.5:
            flags.append("unstable_gaze")
        
        if gaze_data["pupil_size_difference"] > 0.2:
            flags.append("abnormal_pupil_response")
        
        if gaze_data["repeated_off_screen_glances"]:
            flags.append("possible_cheating_indicators")
        
        return flags
    
    @staticmethod
    def _calculate_risk_level(gaze_data: Dict) -> str:
        """Calculate risk level from eye tracking data"""
        
        risk_score = 0.0
        
        if not gaze_data["gaze_on_screen"]:
            risk_score += 0.3
        
        if gaze_data["repeated_off_screen_glances"]:
            risk_score += 0.25
        
        if gaze_data["gaze_stability"] < 0.5:
            risk_score += 0.15
        
        if gaze_data["prolonged_blink"]:
            risk_score += 0.1
        
        if gaze_data["eye_fatigue_indicator"]:
            risk_score += 0.1
        
        if risk_score > 0.7:
            return "critical"
        elif risk_score > 0.5:
            return "high"
        elif risk_score > 0.3:
            return "medium"
        else:
            return "low"
    
    @staticmethod
    async def get_eye_tracking_analytics(session_id: str) -> Dict[str, Any]:
        """Get comprehensive eye tracking analytics for a session"""
        
        try:
            response = supabase_client.table("eye_tracking_data")\
                .select("*")\
                .eq("session_id", session_id)\
                .order("timestamp")\
                .execute()
            
            tracking_data = response.data or []
            
            if not tracking_data:
                return {"error": "No eye tracking data found"}
            
            # Calculate statistics
            total_frames = len(tracking_data)
            off_screen_frames = sum(1 for d in tracking_data if not d.get("gaze_on_screen", True))
            average_gaze_stability = sum(d.get("gaze_stability", 1.0) for d in tracking_data) / total_frames if total_frames > 0 else 0
            average_blinking_rate = sum(d.get("blinking_rate", 0.0) for d in tracking_data) / total_frames if total_frames > 0 else 0
            
            suspicious_patterns = sum(1 for d in tracking_data if d.get("suspicious_eye_pattern", False))
            potential_cheating = sum(1 for d in tracking_data if d.get("potential_cheating_sign", False))
            
            off_screen_percentage = (off_screen_frames / total_frames * 100) if total_frames > 0 else 0
            
            return {
                "session_id": session_id,
                "total_frames_analyzed": total_frames,
                "off_screen_frames": off_screen_frames,
                "off_screen_percentage": off_screen_percentage,
                "average_gaze_stability": average_gaze_stability,
                "average_blinking_rate": average_blinking_rate,
                "suspicious_patterns_detected": suspicious_patterns,
                "potential_cheating_indicators": potential_cheating,
                "eye_fatigue_episodes": sum(1 for d in tracking_data if d.get("eye_fatigue_indicator", False)),
                "gaze_patterns": {
                    "at_keyboard": sum(1 for d in tracking_data if d.get("gaze_at_keyboard", False)),
                    "at_external_object": sum(1 for d in tracking_data if d.get("gaze_at_external_object", False)),
                    "off_screen": off_screen_frames
                },
                "risk_assessment": "high_risk" if off_screen_percentage > 20 else "normal",
                "recommendation": "Manual review required" if suspicious_patterns > 0 else "No action needed"
            }
            
        except Exception as e:
            logger.error(f"Failed to get eye tracking analytics: {str(e)}")
            raise AppError(f"Failed to get eye tracking analytics: {str(e)}", 500)


# ============================================================================
# NOISE DETECTION SERVICE
# ============================================================================

class NoiseDetectionService:
    """
    Advanced noise detection service for proctoring
    - Detects ambient noise levels
    - Identifies speech patterns
    - Detects suspicious audio (external communication)
    - Monitors audio anomalies
    """
    
    @staticmethod
    async def analyze_audio(
        session_id: str,
        audio_data: str,
        duration_seconds: float = 5.0
    ) -> Dict[str, Any]:
        """
        Analyze audio from microphone
        
        Args:
            session_id: Proctoring session ID
            audio_data: Base64 encoded audio data
            duration_seconds: Duration of audio sample
            
        Returns:
            Audio analysis results
        """
        
        try:
            # Use Gemini to analyze audio
            analysis = await gemini_client.analyze_audio_for_proctoring(audio_data)
            
            audio_analysis = {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": duration_seconds,
                
                # Noise levels
                "ambient_noise_level_db": analysis.get("ambient_noise_db", 0),
                "background_noise_detected": analysis.get("background_noise", False),
                "noise_above_threshold": analysis.get("noise_above_threshold", False),
                
                # Speech analysis
                "speech_detected": analysis.get("speech_detected", False),
                "speech_confidence": analysis.get("speech_confidence", 0.0),
                "number_of_speakers": analysis.get("num_speakers", 0),
                "language_detected": analysis.get("language", "unknown"),
                
                # Specific sounds
                "keyboard_clicking_detected": analysis.get("keyboard_sound", False),
                "mouse_clicking_detected": analysis.get("mouse_sound", False),
                "phone_ringing_detected": analysis.get("phone_ring", False),
                "door_knock_detected": analysis.get("door_knock", False),
                "notification_sound_detected": analysis.get("notification_sound", False),
                "footsteps_detected": analysis.get("footsteps", False),
                "paper_rustling_detected": analysis.get("paper_rustling", False),
                "whisper_detected": analysis.get("whisper", False),
                
                # Communication patterns
                "conversation_detected": analysis.get("conversation", False),
                "multiple_voices": analysis.get("multiple_voices", False),
                "external_communication_suspected": analysis.get("external_comm", False),
                "suspicious_audio_pattern": analysis.get("suspicious_pattern", False),
                
                # Quality metrics
                "audio_quality_score": analysis.get("audio_quality", 0.5),
                "signal_to_noise_ratio": analysis.get("snr", 0.0),
                "clipping_detected": analysis.get("clipping", False),
                "audio_degradation": analysis.get("degradation", False),
                
                # Risk indicators
                "potential_cheating_audio": analysis.get("potential_cheating", False),
                "suspicious_sound_pattern": analysis.get("suspicious_sound", False),
                "environment_integrity_concern": analysis.get("env_integrity", False),
                
                # Confidence and recommendations
                "analysis_confidence": analysis.get("confidence", 0.5),
                "violation_probability": analysis.get("violation_prob", 0.0),
                "recommended_action": analysis.get("recommendation", "none"),
                
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Save to database
            response = supabase_client.table("noise_detection_data").insert(audio_analysis).execute()
            
            if response.data:
                logger.info(f"Noise detection data saved for session {session_id}")
            
            return {
                "success": True,
                "analysis_id": audio_analysis["id"],
                "noise_level_db": audio_analysis["ambient_noise_level_db"],
                "speech_detected": audio_analysis["speech_detected"],
                "risk_flags": await NoiseDetectionService._check_audio_flags(audio_analysis),
                "risk_level": NoiseDetectionService._calculate_audio_risk(audio_analysis)
            }
            
        except Exception as e:
            logger.error(f"Audio analysis failed: {str(e)}")
            raise AppError(f"Audio analysis failed: {str(e)}", 500)
    
    @staticmethod
    async def _check_audio_flags(audio_data: Dict) -> List[str]:
        """Check for suspicious audio patterns"""
        
        flags = []
        
        if audio_data["speech_detected"] and audio_data["number_of_speakers"] > 1:
            flags.append("multiple_speakers_detected")
        
        if audio_data["conversation_detected"]:
            flags.append("conversation_in_background")
        
        if audio_data["external_communication_suspected"]:
            flags.append("possible_external_communication")
        
        if audio_data["noise_above_threshold"]:
            flags.append("excessive_background_noise")
        
        if audio_data["phone_ringing_detected"]:
            flags.append("phone_activity_detected")
        
        if audio_data["whisper_detected"]:
            flags.append("whisper_detected_suspicious")
        
        if audio_data["suspicious_audio_pattern"]:
            flags.append("anomalous_audio_pattern")
        
        if audio_data["potential_cheating_audio"]:
            flags.append("potential_cheating_indicators")
        
        return flags
    
    @staticmethod
    def _calculate_audio_risk(audio_data: Dict) -> str:
        """Calculate audio risk level"""
        
        risk_score = 0.0
        
        if audio_data["speech_detected"] and audio_data["number_of_speakers"] > 1:
            risk_score += 0.35
        
        if audio_data["external_communication_suspected"]:
            risk_score += 0.3
        
        if audio_data["noise_above_threshold"]:
            risk_score += 0.15
        
        if audio_data["whisper_detected"]:
            risk_score += 0.15
        
        if audio_data["suspicious_audio_pattern"]:
            risk_score += 0.1
        
        if risk_score > 0.7:
            return "critical"
        elif risk_score > 0.5:
            return "high"
        elif risk_score > 0.3:
            return "medium"
        else:
            return "low"
    
    @staticmethod
    async def get_audio_analytics(session_id: str) -> Dict[str, Any]:
        """Get comprehensive audio analytics for a session"""
        
        try:
            response = supabase_client.table("noise_detection_data")\
                .select("*")\
                .eq("session_id", session_id)\
                .order("timestamp")\
                .execute()
            
            audio_data = response.data or []
            
            if not audio_data:
                return {"error": "No audio data found"}
            
            # Calculate statistics
            total_samples = len(audio_data)
            avg_noise_level = sum(d.get("ambient_noise_level_db", 0) for d in audio_data) / total_samples if total_samples > 0 else 0
            speech_detected_count = sum(1 for d in audio_data if d.get("speech_detected", False))
            suspicious_patterns = sum(1 for d in audio_data if d.get("suspicious_audio_pattern", False))
            external_comm_suspected = sum(1 for d in audio_data if d.get("external_communication_suspected", False))
            
            return {
                "session_id": session_id,
                "total_samples": total_samples,
                "average_noise_level_db": avg_noise_level,
                "speech_detection_rate": (speech_detected_count / total_samples * 100) if total_samples > 0 else 0,
                "suspicious_patterns_detected": suspicious_patterns,
                "external_communication_suspected_count": external_comm_suspected,
                "suspicious_sounds": {
                    "keyboard": sum(1 for d in audio_data if d.get("keyboard_clicking_detected", False)),
                    "mouse": sum(1 for d in audio_data if d.get("mouse_clicking_detected", False)),
                    "phone": sum(1 for d in audio_data if d.get("phone_ringing_detected", False)),
                    "conversation": sum(1 for d in audio_data if d.get("conversation_detected", False))
                },
                "risk_assessment": "high_risk" if suspicious_patterns > 2 or external_comm_suspected > 0 else "normal",
                "recommendation": "Manual review required" if suspicious_patterns > 1 else "No action needed"
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio analytics: {str(e)}")
            raise AppError(f"Failed to get audio analytics: {str(e)}", 500)


# ============================================================================
# FACE RECOGNITION SERVICE
# ============================================================================

class FaceRecognitionService:
    """
    Advanced face recognition service for proctoring
    - Identity verification (matches registered student)
    - Face spoofing detection (prevents use of photos/videos)
    - Facial expression analysis
    - Liveness detection
    """
    
    @staticmethod
    async def verify_student_identity(
        session_id: str,
        user_id: str,
        frame_data: str,
        registered_face_embedding: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify student identity from frame
        
        Args:
            session_id: Proctoring session ID
            user_id: User ID
            frame_data: Base64 encoded frame
            registered_face_embedding: Previously stored face embedding
            
        Returns:
            Identity verification results
        """
        
        try:
            # Use Gemini for face analysis
            analysis = await gemini_client.analyze_face_recognition(frame_data)
            
            face_verification = {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                
                # Face detection
                "face_detected": analysis.get("face_detected", False),
                "number_of_faces": analysis.get("num_faces", 0),
                "face_quality": analysis.get("face_quality", 0.0),
                "face_area_percentage": analysis.get("face_area_pct", 0.0),
                
                # Identity verification
                "identity_match_confidence": analysis.get("identity_confidence", 0.0),
                "identity_verified": analysis.get("identity_verified", False),
                "identity_mismatch_detected": analysis.get("identity_mismatch", False),
                
                # Liveness detection
                "liveness_score": analysis.get("liveness_score", 0.0),
                "liveness_detected": analysis.get("liveness_detected", False),
                "spoofing_detected": analysis.get("spoofing_detected", False),
                "spoofing_confidence": analysis.get("spoofing_confidence", 0.0),
                "presentation_attack_detected": analysis.get("presentation_attack", False),
                
                # Facial characteristics
                "age_estimated": analysis.get("age_estimated", 0),
                "gender_detected": analysis.get("gender", "unknown"),
                "ethnicity_detected": analysis.get("ethnicity", "unknown"),
                "expression_neutral": analysis.get("neutral_expression", False),
                "expression_anomaly": analysis.get("expression_anomaly", False),
                
                # Eye and mouth analysis
                "eyes_open": analysis.get("eyes_open", True),
                "mouth_open": analysis.get("mouth_open", False),
                "blinking": analysis.get("blinking", False),
                "smile_detected": analysis.get("smile", False),
                
                # Facial landmarks
                "face_landmarks_detected": analysis.get("landmarks_detected", 0),
                "landmarks_quality": analysis.get("landmarks_quality", 0.0),
                
                # Face orientation
                "face_yaw": analysis.get("yaw", 0.0),
                "face_pitch": analysis.get("pitch", 0.0),
                "face_roll": analysis.get("roll", 0.0),
                "frontal_face": analysis.get("frontal", False),
                
                # Suspicious indicators
                "masked_face_detected": analysis.get("mask_detected", False),
                "face_covered_detected": analysis.get("face_covered", False),
                "glasses_detected": analysis.get("glasses_detected", False),
                "sun_glasses_detected": analysis.get("sunglasses", False),
                "face_obscured": analysis.get("face_obscured", False),
                
                # Lighting and quality
                "lighting_conditions": analysis.get("lighting", "normal"),
                "overexposed": analysis.get("overexposed", False),
                "underexposed": analysis.get("underexposed", False),
                "shadow_on_face": analysis.get("shadow", False),
                
                # Anti-spoofing
                "anti_spoofing_score": analysis.get("anti_spoofing_score", 0.0),
                "texture_analysis_score": analysis.get("texture_score", 0.0),
                "depth_map_quality": analysis.get("depth_quality", 0.0),
                
                # Risk indicators
                "identity_risk": analysis.get("identity_risk", False),
                "potential_spoofing_risk": analysis.get("spoofing_risk", False),
                "suspicious_face_pattern": analysis.get("suspicious_pattern", False),
                
                "verification_confidence": analysis.get("verification_confidence", 0.5),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Save to database
            response = supabase_client.table("face_recognition_data").insert(face_verification).execute()
            
            if response.data:
                logger.info(f"Face verification data saved for session {session_id}")
            
            return {
                "success": True,
                "verification_id": face_verification["id"],
                "identity_verified": face_verification["identity_verified"],
                "liveness_detected": face_verification["liveness_detected"],
                "spoofing_detected": face_verification["spoofing_detected"],
                "risk_flags": await FaceRecognitionService._check_face_flags(face_verification),
                "risk_level": FaceRecognitionService._calculate_face_risk(face_verification),
                "verification_confidence": face_verification["verification_confidence"]
            }
            
        except Exception as e:
            logger.error(f"Face recognition failed: {str(e)}")
            raise AppError(f"Face recognition failed: {str(e)}", 500)
    
    @staticmethod
    async def _check_face_flags(face_data: Dict) -> List[str]:
        """Check for suspicious face patterns"""
        
        flags = []
        
        if not face_data["face_detected"]:
            flags.append("no_face_detected")
        
        if face_data["number_of_faces"] > 1:
            flags.append("multiple_faces_detected")
        
        if face_data["identity_mismatch_detected"]:
            flags.append("identity_mismatch")
        
        if face_data["spoofing_detected"]:
            flags.append("presentation_attack_detected")
        
        if face_data["presentation_attack_detected"]:
            flags.append("spoofing_attempt_suspected")
        
        if not face_data["liveness_detected"] and face_data["liveness_score"] < 0.5:
            flags.append("possible_photo_spoofing")
        
        if face_data["masked_face_detected"] or face_data["face_covered_detected"]:
            flags.append("face_obscured_or_masked")
        
        if face_data["expression_anomaly"]:
            flags.append("unusual_facial_expression")
        
        if face_data["identity_risk"]:
            flags.append("identity_verification_failed")
        
        if face_data["potential_spoofing_risk"]:
            flags.append("anti_spoofing_check_failed")
        
        return flags
    
    @staticmethod
    def _calculate_face_risk(face_data: Dict) -> str:
        """Calculate face recognition risk level"""
        
        risk_score = 0.0
        
        if not face_data["face_detected"]:
            risk_score += 0.4
        
        if face_data["spoofing_detected"]:
            risk_score += 0.35
        
        if face_data["identity_mismatch_detected"]:
            risk_score += 0.3
        
        if not face_data["liveness_detected"]:
            risk_score += 0.25
        
        if face_data["masked_face_detected"]:
            risk_score += 0.15
        
        if face_data["expression_anomaly"]:
            risk_score += 0.1
        
        if risk_score > 0.7:
            return "critical"
        elif risk_score > 0.5:
            return "high"
        elif risk_score > 0.3:
            return "medium"
        else:
            return "low"
    
    @staticmethod
    async def get_face_verification_analytics(session_id: str) -> Dict[str, Any]:
        """Get comprehensive face verification analytics for a session"""
        
        try:
            response = supabase_client.table("face_recognition_data")\
                .select("*")\
                .eq("session_id", session_id)\
                .order("timestamp")\
                .execute()
            
            face_data = response.data or []
            
            if not face_data:
                return {"error": "No face recognition data found"}
            
            # Calculate statistics
            total_frames = len(face_data)
            identity_verified_count = sum(1 for d in face_data if d.get("identity_verified", False))
            liveness_detected_count = sum(1 for d in face_data if d.get("liveness_detected", False))
            spoofing_detected_count = sum(1 for d in face_data if d.get("spoofing_detected", False))
            identity_mismatch_count = sum(1 for d in face_data if d.get("identity_mismatch_detected", False))
            
            avg_identity_confidence = sum(d.get("identity_match_confidence", 0) for d in face_data) / total_frames if total_frames > 0 else 0
            avg_liveness_score = sum(d.get("liveness_score", 0) for d in face_data) / total_frames if total_frames > 0 else 0
            
            return {
                "session_id": session_id,
                "total_frames_analyzed": total_frames,
                "identity_verification_rate": (identity_verified_count / total_frames * 100) if total_frames > 0 else 0,
                "liveness_detection_rate": (liveness_detected_count / total_frames * 100) if total_frames > 0 else 0,
                "average_identity_confidence": avg_identity_confidence,
                "average_liveness_score": avg_liveness_score,
                "spoofing_attempts_detected": spoofing_detected_count,
                "identity_mismatches_detected": identity_mismatch_count,
                "masked_face_count": sum(1 for d in face_data if d.get("masked_face_detected", False)),
                "face_quality_issues": sum(1 for d in face_data if d.get("face_quality", 1.0) < 0.5),
                "overall_identity_status": "verified" if avg_identity_confidence > 0.85 else "uncertain",
                "spoofing_risk": "high_risk" if spoofing_detected_count > 0 else "normal",
                "recommendation": "Escalate to manual review" if identity_mismatch_count > 0 or spoofing_detected_count > 0 else "No action needed"
            }
            
        except Exception as e:
            logger.error(f"Failed to get face verification analytics: {str(e)}")
            raise AppError(f"Failed to get face verification analytics: {str(e)}", 500)


# ============================================================================
# UNIFIED ADVANCED PROCTORING SERVICE
# ============================================================================

class AdvancedProctoringService:
    """
    Unified service combining all advanced proctoring features
    """
    
    @staticmethod
    async def start_advanced_monitoring(
        session_id: str,
        user_id: str,
        assessment_id: str
    ) -> Dict[str, Any]:
        """Start advanced proctoring with all features"""
        
        try:
            response = supabase_client.table("proctoring_sessions")\
                .select("*")\
                .eq("id", session_id)\
                .single()\
                .execute()
            
            if not response.data:
                raise AppError("Session not found", 404)
            
            # Enable advanced features
            update_data = {
                "advanced_proctoring_enabled": True,
                "eye_tracking_enabled": True,
                "noise_detection_enabled": True,
                "face_recognition_enabled": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            supabase_client.table("proctoring_sessions").update(update_data)\
                .eq("id", session_id).execute()
            
            logger.info(f"Advanced proctoring started for session {session_id}")
            
            return {
                "success": True,
                "session_id": session_id,
                "advanced_features_enabled": {
                    "eye_tracking": True,
                    "noise_detection": True,
                    "face_recognition": True
                },
                "message": "Advanced proctoring monitoring activated"
            }
            
        except Exception as e:
            logger.error(f"Failed to start advanced monitoring: {str(e)}")
            raise
    
    @staticmethod
    async def process_advanced_frame(
        session_id: str,
        frame_data: str,
        audio_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process frame with all advanced proctoring features"""
        
        results = {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "features_analyzed": []
        }
        
        try:
            # Eye tracking
            eye_analysis = await EyeTrackingService.analyze_eye_gaze(session_id, frame_data)
            results["eye_tracking"] = eye_analysis
            results["features_analyzed"].append("eye_tracking")
            
        except Exception as e:
            logger.warning(f"Eye tracking failed: {str(e)}")
            results["eye_tracking"] = {"error": str(e)}
        
        try:
            # Noise detection
            if audio_data:
                audio_analysis = await NoiseDetectionService.analyze_audio(session_id, audio_data)
                results["noise_detection"] = audio_analysis
                results["features_analyzed"].append("noise_detection")
            
        except Exception as e:
            logger.warning(f"Noise detection failed: {str(e)}")
            results["noise_detection"] = {"error": str(e)}
        
        try:
            # Face recognition
            face_analysis = await FaceRecognitionService.verify_student_identity(session_id, "", frame_data)
            results["face_recognition"] = face_analysis
            results["features_analyzed"].append("face_recognition")
            
        except Exception as e:
            logger.warning(f"Face recognition failed: {str(e)}")
            results["face_recognition"] = {"error": str(e)}
        
        # Aggregate risk level
        risk_levels = []
        if "eye_tracking" in results and "risk_level" in results["eye_tracking"]:
            risk_levels.append(results["eye_tracking"]["risk_level"])
        if "noise_detection" in results and "risk_level" in results["noise_detection"]:
            risk_levels.append(results["noise_detection"]["risk_level"])
        if "face_recognition" in results and "risk_level" in results["face_recognition"]:
            risk_levels.append(results["face_recognition"]["risk_level"])
        
        # Calculate overall risk
        critical_count = sum(1 for r in risk_levels if r == "critical")
        high_count = sum(1 for r in risk_levels if r == "high")
        
        if critical_count > 0:
            results["overall_risk"] = "critical"
        elif high_count > 1:
            results["overall_risk"] = "high"
        elif high_count > 0:
            results["overall_risk"] = "medium"
        else:
            results["overall_risk"] = "low"
        
        return results
    
    @staticmethod
    async def get_comprehensive_analytics(session_id: str) -> Dict[str, Any]:
        """Get comprehensive analytics for all advanced features"""
        
        analytics = {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            eye_analytics = await EyeTrackingService.get_eye_tracking_analytics(session_id)
            analytics["eye_tracking"] = eye_analytics
        except Exception as e:
            logger.warning(f"Eye tracking analytics failed: {str(e)}")
            analytics["eye_tracking"] = {"error": str(e)}
        
        try:
            audio_analytics = await NoiseDetectionService.get_audio_analytics(session_id)
            analytics["noise_detection"] = audio_analytics
        except Exception as e:
            logger.warning(f"Audio analytics failed: {str(e)}")
            analytics["noise_detection"] = {"error": str(e)}
        
        try:
            face_analytics = await FaceRecognitionService.get_face_verification_analytics(session_id)
            analytics["face_recognition"] = face_analytics
        except Exception as e:
            logger.warning(f"Face analytics failed: {str(e)}")
            analytics["face_recognition"] = {"error": str(e)}
        
        return analytics
