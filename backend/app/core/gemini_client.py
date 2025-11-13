from typing import Any, Dict
import google.generativeai as genai
from app.config import settings


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
        Analyze a proctoring snapshot image for suspicious activity
        
        Args:
            image_data: Base64 encoded image data
            
        Returns:
            Dictionary with analysis results
        """
        if not self.model:
            # Return default analysis if Gemini is not configured
            return {
                "faces_detected": 1,
                "multiple_faces": False,
                "no_face_detected": False,
                "suspicious_activity": False,
                "confidence": 0.8,
                "analysis": "Gemini AI not configured"
            }
        
        try:
            # Decode base64 image
            import base64
            from io import BytesIO
            from PIL import Image
            
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
            
            # Create prompt for proctoring analysis
            prompt = """
            Analyze this proctoring image and provide a JSON response with:
            - faces_detected: number of faces detected (0, 1, or more)
            - multiple_faces: boolean (true if more than 1 face)
            - no_face_detected: boolean (true if 0 faces)
            - suspicious_activity: boolean (true if suspicious behavior detected)
            - confidence: float between 0 and 1
            
            Look for:
            - Multiple people in frame
            - No person visible
            - Person looking away from screen
            - Phone or other devices visible
            - Unusual behavior
            
            Return only valid JSON.
            """
            
            # Generate analysis
            response = self.model.generate_content([prompt, image])
            
            # Parse response (assuming JSON format)
            import json
            try:
                # Try to extract JSON from response
                response_text = response.text.strip()
                # Remove markdown code blocks if present
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                response_text = response_text.strip()
                
                analysis = json.loads(response_text)
            except:
                # Fallback if JSON parsing fails
                analysis = {
                    "faces_detected": 1,
                    "multiple_faces": False,
                    "no_face_detected": False,
                    "suspicious_activity": False,
                    "confidence": 0.7,
                    "raw_response": response.text
                }
            
            return {
                "faces_detected": analysis.get("faces_detected", 1),
                "multiple_faces": analysis.get("multiple_faces", False),
                "no_face_detected": analysis.get("no_face_detected", False),
                "suspicious_activity": analysis.get("suspicious_activity", False),
                "confidence": analysis.get("confidence", 0.7),
                "analysis": analysis
            }
            
        except Exception as e:
            # Return safe default on error
            return {
                "faces_detected": 1,
                "multiple_faces": False,
                "no_face_detected": False,
                "suspicious_activity": False,
                "confidence": 0.5,
                "error": str(e)
            }


# Singleton instance
gemini_client = GeminiClient()

