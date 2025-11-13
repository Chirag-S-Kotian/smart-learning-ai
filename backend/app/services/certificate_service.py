from typing import Dict, Any
from app.core.supabase_client import supabase_client


class CertificateService:
    """Service for certificate generation and verification"""
    
    async def generate_certificate(self, attempt_id: str) -> Dict[str, Any]:
        """
        Generate a certificate for a completed assessment attempt
        
        Args:
            attempt_id: Assessment attempt ID
            
        Returns:
            Dictionary with certificate data
        """
        # Get attempt details
        attempt = supabase_client.table("assessment_attempts").select(
            "*, assessments(*, courses(*))"
        ).eq("id", attempt_id).single().execute()
        
        if not attempt.data:
            raise Exception("Assessment attempt not found")
        
        attempt_data = attempt.data
        assessment = attempt_data.get("assessments", {})
        course = assessment.get("courses", {})
        
        # Check if certificate already exists
        existing = supabase_client.table("certificates").select("*").eq(
            "assessment_id", assessment["id"]
        ).eq("user_id", attempt_data["user_id"]).execute()
        
        if existing.data:
            return {"certificate": existing.data[0]}
        
        # Generate certificate number using database function
        cert_number_result = supabase_client.rpc("generate_certificate_number").execute()
        certificate_number = cert_number_result.data if cert_number_result.data else f"CERT-{attempt_id[:8]}"
        
        # Create certificate
        certificate_data = {
            "certificate_number": certificate_number,
            "user_id": attempt_data["user_id"],
            "assessment_id": assessment["id"],
            "course_id": course.get("id"),
            "score": attempt_data.get("score", 0),
            "percentage": attempt_data.get("percentage", 0),
            "grade": self._calculate_grade(attempt_data.get("percentage", 0)),
            "verification_code": f"VER-{attempt_id[:8]}-{certificate_number[:8]}",
            "is_verified": True
        }
        
        result = supabase_client.table("certificates").insert(certificate_data).execute()
        
        # Trigger badge awards
        supabase_client.rpc("award_badges_on_completion").execute()
        
        return {"certificate": result.data[0]}
    
    def verify_certificate(self, verification_code: str) -> Dict[str, Any]:
        """
        Verify a certificate by verification code
        
        Args:
            verification_code: Certificate verification code
            
        Returns:
            Dictionary with verification result and certificate data
        """
        result = supabase_client.table("certificates").select(
            "*, users(full_name), assessments(title), courses(title)"
        ).eq("verification_code", verification_code).single().execute()
        
        if not result.data:
            return {
                "valid": False,
                "certificate": None,
                "message": "Certificate not found"
            }
        
        certificate = result.data
        certificate["user_name"] = certificate.get("users", {}).get("full_name")
        certificate["assessment_title"] = certificate.get("assessments", {}).get("title")
        certificate["course_title"] = certificate.get("courses", {}).get("title")
        
        # Remove nested objects
        for key in ["users", "assessments", "courses"]:
            if key in certificate:
                del certificate[key]
        
        return {
            "valid": True,
            "certificate": certificate,
            "message": "Certificate verified successfully"
        }
    
    def _calculate_grade(self, percentage: float) -> str:
        """Calculate grade based on percentage"""
        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        else:
            return "F"


# Singleton instance
certificate_service = CertificateService()

