from typing import Any, Dict
import google.generativeai as genai
from app.config import settings
import json


class GeminiClient:
    """Client for Google Gemini AI integration"""
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None
    
    async def analyze_proctoring_image(self, image_data: str) -> Dict[str, Any]:
        """
        Comprehensive proctoring snapshot analysis using Gemini AI
        Detects multiple violation scenarios
        
        Args:
            image_data: Base64 encoded image data
            
        Returns:
            Dictionary with detailed analysis results
        """
        if not self.model:
            return self._default_analysis()
        
        try:
            # Decode and prepare image
            import base64
            from io import BytesIO
            from PIL import Image
            
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
            
            # Advanced proctoring prompt with multiple detection scenarios
            prompt = """
            Analyze this exam proctoring image and provide a comprehensive JSON response with the following analysis:
            
            DETECTION SCENARIOS:
            1. Face Detection
               - faces_detected: number of faces (0, 1, 2+)
               - face_visible: boolean (is test-taker's face visible)
               - eye_contact: boolean (looking at screen)
            
            2. Multiple Persons
               - multiple_faces: boolean
               - additional_people_count: number of other people
            
            3. Screen/Device Analysis
               - phone_detected: boolean
               - external_monitor_detected: boolean
               - tablet_detected: boolean
               - other_device_detected: boolean
            
            4. Head Position & Behavior
               - head_tilted_away: boolean (looking away from screen)
               - looking_down: boolean (checking something below)
               - looking_up: boolean (checking something above)
               - extreme_head_angle: boolean (very unnatural position)
            
            5. Environmental Factors
               - bright_light_glare: boolean
               - dark_lighting: boolean
               - shadows_on_face: boolean
            
            6. Suspicious Activity
               - suspicious_hand_gesture: boolean
               - object_in_mouth: boolean (pen, fingers, food)
               - reading_from_paper: boolean
               - unusual_body_position: boolean
            
            7. Background Analysis
               - books_visible: boolean
               - notes_visible: boolean
               - help_text_visible: boolean
               - other_screens_visible: boolean
            
            8. Overall Assessment
               - overall_suspicion_score: float (0-1, where 1 is most suspicious)
               - confidence_score: float (0-1, reliability of analysis)
               - primary_violation: string (if any, the most serious violation detected)
               - violation_severity: string (low, medium, high, critical)
               - recommended_action: string (allow, warn, flag_for_review, terminate)
            
            Return ONLY valid JSON with no markdown formatting.
            """
            
            response = self.model.generate_content([prompt, image])
            analysis_data = self._parse_gemini_response(response.text)
            
            return {
                "success": True,
                "analysis": analysis_data,
                "faces_detected": analysis_data.get("faces_detected", 0),
                "multiple_faces": analysis_data.get("multiple_faces", False),
                "no_face_detected": analysis_data.get("faces_detected", 0) == 0,
                "suspicious_activity": analysis_data.get("overall_suspicion_score", 0) > 0.5,
                "confidence": analysis_data.get("confidence_score", 0.7),
                "description": analysis_data.get("primary_violation", "No violations detected"),
                "severity": analysis_data.get("violation_severity", "low")
            }
            
        except Exception as e:
            return self._error_analysis(str(e))
    
    async def analyze_session_behavior(self, snapshots: list) -> Dict[str, Any]:
        """
        Analyze behavior patterns across multiple snapshots during a session
        
        Args:
            snapshots: List of snapshot analyses
            
        Returns:
            Session-level behavior analysis
        """
        if not snapshots:
            return {
                "pattern": "insufficient_data",
                "behavior_score": 0,
                "trend": "unknown"
            }
        
        try:
            # Analyze trends
            suspicion_scores = [s.get("analysis", {}).get("overall_suspicion_score", 0) for s in snapshots]
            face_loss_count = sum(1 for s in snapshots if s.get("faces_detected", 0) == 0)
            
            avg_suspicion = sum(suspicion_scores) / len(suspicion_scores) if suspicion_scores else 0
            face_loss_percentage = (face_loss_count / len(snapshots) * 100) if snapshots else 0
            
            # Determine behavior pattern
            pattern = self._determine_behavior_pattern(snapshots, avg_suspicion, face_loss_percentage)
            
            # Trend analysis
            trend = "stable"
            if len(suspicion_scores) > 1:
                if suspicion_scores[-1] > suspicion_scores[0] * 1.5:
                    trend = "deteriorating"
                elif suspicion_scores[-1] < suspicion_scores[0] * 0.5:
                    trend = "improving"
            
            return {
                "pattern": pattern,
                "average_suspicion_score": round(avg_suspicion, 2),
                "face_loss_percentage": round(face_loss_percentage, 1),
                "total_violations": sum(1 for s in snapshots if s.get("suspicious_activity")),
                "trend": trend,
                "recommendation": self._get_session_recommendation(pattern, avg_suspicion, trend)
            }
        
        except Exception as e:
            return {"error": str(e), "pattern": "analysis_error"}
    
    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response to extract JSON"""
        try:
            text = response_text.strip()
            
            # Remove markdown code blocks
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            text = text.strip()
            analysis = json.loads(text)
            return analysis
            
        except json.JSONDecodeError:
            # Fallback structure if parsing fails
            return {
                "faces_detected": 1,
                "face_visible": True,
                "multiple_faces": False,
                "phone_detected": False,
                "overall_suspicion_score": 0.3,
                "confidence_score": 0.6,
                "primary_violation": "Unable to analyze",
                "violation_severity": "low",
                "recommended_action": "allow"
            }
    
    def _determine_behavior_pattern(self, snapshots: list, avg_suspicion: float, face_loss_pct: float) -> str:
        """Determine student behavior pattern from analysis"""
        
        if face_loss_pct > 30:
            return "frequent_face_loss"
        
        if avg_suspicion > 0.8:
            return "highly_suspicious"
        elif avg_suspicion > 0.6:
            return "moderately_suspicious"
        
        multiple_faces = sum(1 for s in snapshots if s.get("multiple_faces", False))
        if multiple_faces > len(snapshots) * 0.3:
            return "multiple_people_detected"
        
        phone_detections = sum(1 for s in snapshots if s.get("analysis", {}).get("phone_detected", False))
        if phone_detections > 0:
            return "device_usage_detected"
        
        reading_detected = sum(1 for s in snapshots if s.get("analysis", {}).get("reading_from_paper", False))
        if reading_detected > 0:
            return "unauthorized_materials"
        
        return "normal_behavior"
    
    def _get_session_recommendation(self, pattern: str, avg_suspicion: float, trend: str) -> str:
        """Get recommendation based on session analysis"""
        
        suspicious_patterns = ["highly_suspicious", "multiple_people_detected", "unauthorized_materials"]
        
        if pattern in suspicious_patterns:
            if trend == "deteriorating":
                return "terminate_exam_immediately"
            return "flag_for_manual_review"
        
        if pattern == "moderately_suspicious":
            return "send_warning_and_monitor"
        
        if pattern == "frequent_face_loss":
            return "request_camera_repositioning"
        
        if avg_suspicion > 0.7:
            return "escalate_to_proctor"
        
        return "allow_to_continue"
    
    def _default_analysis(self) -> Dict[str, Any]:
        """Return default analysis when Gemini not configured"""
        return {
            "success": False,
            "analysis": {
                "faces_detected": 1,
                "multiple_faces": False,
                "phone_detected": False,
                "overall_suspicion_score": 0.5,
                "confidence_score": 0.4,
                "recommended_action": "allow"
            },
            "faces_detected": 1,
            "multiple_faces": False,
            "no_face_detected": False,
            "suspicious_activity": False,
            "confidence": 0.4,
            "description": "Gemini AI not configured",
            "severity": "low"
        }
    
    def _error_analysis(self, error: str) -> Dict[str, Any]:
        """Return safe default on error"""
        return {
            "success": False,
            "error": error,
            "analysis": {
                "faces_detected": 1,
                "confidence_score": 0.3,
                "recommended_action": "manual_review"
            },
            "faces_detected": 1,
            "multiple_faces": False,
            "no_face_detected": False,
            "suspicious_activity": False,
            "confidence": 0.3,
            "severity": "medium"
        }


# Singleton instance
gemini_client = GeminiClient()

