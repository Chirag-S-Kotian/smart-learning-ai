"""
Certificate and Badges Generation Service
Handles certificate generation for completed courses/exams and badge awards
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.core.supabase_client import supabase_client
import logging

logger = logging.getLogger(__name__)


class CertificateService:
    """Service for certificate generation, badge awards, and credential management"""
    
    # Badge definitions with criteria
    BADGES = {
        "first_course": {
            "name": "🎓 First Course",
            "description": "Completed your first course",
            "icon": "🎓",
            "category": "milestone",
            "criteria": {"type": "first_completion"}
        },
        "perfect_score": {
            "name": "⭐ Perfect Score",
            "description": "Achieved 100% on an exam",
            "icon": "⭐",
            "category": "achievement",
            "criteria": {"type": "exam_score", "score": 100}
        },
        "high_achiever": {
            "name": "🏆 High Achiever",
            "description": "Completed 5 courses with 85%+ average",
            "icon": "🏆",
            "category": "achievement",
            "criteria": {"type": "multiple_courses", "count": 5, "avg_score": 85}
        },
        "consistency": {
            "name": "🔥 Consistency",
            "description": "Completed 10 courses",
            "icon": "🔥",
            "category": "milestone",
            "criteria": {"type": "course_count", "count": 10}
        },
        "excellence": {
            "name": "👑 Excellence",
            "description": "Completed 20 courses with 90%+ average",
            "icon": "👑",
            "category": "achievement",
            "criteria": {"type": "multiple_courses", "count": 20, "avg_score": 90}
        },
        "speed_demon": {
            "name": "⚡ Speed Demon",
            "description": "Completed a course in less than 1 day",
            "icon": "⚡",
            "category": "achievement",
            "criteria": {"type": "fast_completion", "days": 1}
        },
        "time_investor": {
            "name": "📚 Time Investor",
            "description": "Spent 50+ hours on learning",
            "icon": "📚",
            "category": "milestone",
            "criteria": {"type": "watch_time", "hours": 50}
        },
        "master": {
            "name": "🎯 Master",
            "description": "Completed all courses in a specialization",
            "icon": "🎯",
            "category": "achievement",
            "criteria": {"type": "specialization_complete"}
        }
    }
    
    async def generate_course_completion_certificate(
        self,
        user_id: str,
        course_id: str
    ) -> Dict[str, Any]:
        """
        Generate certificate for course completion
        
        Args:
            user_id: Student user ID
            course_id: Completed course ID
            
        Returns:
            Certificate data with ID and verification code
        """
        try:
            # Get course and user details
            course_result = supabase_client.table("courses").select(
                "id, title, description, instructor_id, duration_hours"
            ).eq("id", course_id).single().execute()
            
            if not course_result.data:
                raise Exception("Course not found")
            
            course = course_result.data
            
            # Check if certificate already exists
            existing = supabase_client.table("certificates").select("*").eq(
                "user_id", user_id
            ).eq("course_id", course_id).eq("type", "course_completion").execute()
            
            if existing.data:
                logger.info(f"Certificate already exists for user {user_id}, course {course_id}")
                return {
                    "certificate_id": existing.data[0]["id"],
                    "certificate_number": existing.data[0]["certificate_number"],
                    "verification_code": existing.data[0]["verification_code"],
                    "already_exists": True
                }
            
            # Generate unique certificate number and verification code
            certificate_id = str(uuid.uuid4())
            certificate_number = f"CERT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            verification_code = f"VER-{certificate_id[:8]}-{uuid.uuid4().hex[:12].upper()}"
            
            # Get user's course progress for additional data
            progress_result = supabase_client.table("course_progress").select(
                "completion_percentage, total_watch_time_minutes"
            ).eq("user_id", user_id).eq("course_id", course_id).single().execute()
            
            progress = progress_result.data if progress_result.data else {}
            
            # Create certificate record
            certificate_data = {
                "id": certificate_id,
                "certificate_number": certificate_number,
                "user_id": user_id,
                "course_id": course_id,
                "assessment_id": None,
                "type": "course_completion",
                "title": f"Certificate of Completion - {course['title']}",
                "issued_date": datetime.now(timezone.utc).isoformat(),
                "completion_percentage": progress.get("completion_percentage", 100),
                "total_watch_time_minutes": progress.get("total_watch_time_minutes", 0),
                "grade": None,
                "score": None,
                "verification_code": verification_code,
                "is_verified": True,
                "instructor_id": course.get("instructor_id"),
                "course_duration_hours": course.get("duration_hours", 0)
            }
            
            # Update issued_date to ISO format
            certificate_data["issued_date"] = datetime.now(timezone.utc).isoformat()
            result = supabase_client.table("certificates").insert(certificate_data).execute()
            
            logger.info(f"Certificate generated for user {user_id}, course {course_id}")
            
            # Award badges for course completion
            await self._award_completion_badges(user_id, course_id)
            
            return {
                "certificate_id": certificate_id,
                "certificate_number": certificate_number,
                "verification_code": verification_code,
                "title": certificate_data["title"],
                "issued_date": certificate_data["issued_date"]
            }
        
        except Exception as e:
            logger.error(f"Error generating course certificate: {str(e)}")
            raise
    
    async def generate_exam_certificate(
        self,
        user_id: str,
        assessment_id: str,
        score: float,
        percentage: float
    ) -> Dict[str, Any]:
        """
        Generate certificate for exam completion
        
        Args:
            user_id: Student user ID
            assessment_id: Assessment ID
            score: Raw score
            percentage: Score percentage (0-100)
            
        Returns:
            Certificate data with ID and verification code
        """
        try:
            # Get assessment details
            assessment_result = supabase_client.table("assessments").select(
                "id, title, course_id, total_points, courses(title)"
            ).eq("id", assessment_id).single().execute()
            
            if not assessment_result.data:
                raise Exception("Assessment not found")
            
            assessment = assessment_result.data
            
            # Check if passing score (typically 60%)
            if percentage < 60:
                logger.warning(f"Score {percentage}% is below passing threshold for user {user_id}")
                return {"error": "Score below passing threshold", "percentage": percentage}
            
            # Check if certificate already exists
            existing = supabase_client.table("certificates").select("*").eq(
                "user_id", user_id
            ).eq("assessment_id", assessment_id).eq("type", "exam_completion").execute()
            
            if existing.data:
                return {
                    "certificate_id": existing.data[0]["id"],
                    "already_exists": True
                }
            
            # Generate unique certificate number and verification code
            certificate_id = str(uuid.uuid4())
            certificate_number = f"EXAM-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            verification_code = f"VER-{certificate_id[:8]}-{uuid.uuid4().hex[:12].upper()}"
            
            grade = self._calculate_grade(percentage)
            
            # Create certificate record
            certificate_data = {
                "id": certificate_id,
                "certificate_number": certificate_number,
                "user_id": user_id,
                "course_id": assessment.get("course_id"),
                "assessment_id": assessment_id,
                "type": "exam_completion",
                "title": f"Certificate of Achievement - {assessment['title']}",
                "issued_date": datetime.now(timezone.utc).isoformat(),
                "score": score,
                "percentage": percentage,
                "grade": grade,
                "verification_code": verification_code,
                "is_verified": True
            }
            
            result = supabase_client.table("certificates").insert(certificate_data).execute()
            
            logger.info(f"Exam certificate generated for user {user_id}, assessment {assessment_id}")
            
            # Award badges for exam achievement
            await self._award_exam_badges(user_id, percentage)
            
            return {
                "certificate_id": certificate_id,
                "certificate_number": certificate_number,
                "verification_code": verification_code,
                "title": certificate_data["title"],
                "grade": grade,
                "percentage": percentage,
                "issued_date": certificate_data["issued_date"]
            }
        
        except Exception as e:
            logger.error(f"Error generating exam certificate: {str(e)}")
            raise
    
    async def _award_completion_badges(self, user_id: str, course_id: str) -> None:
        """Award badges based on course completion"""
        try:
            # Check if this is the first course
            course_count = supabase_client.table("certificates").select(
                "id", count="exact"
            ).eq("user_id", user_id).eq("type", "course_completion").execute()
            
            if course_count.count == 0:
                # Award first course badge
                await self.award_badge(user_id, "first_course")
            
            # Check for consistency badge (10 courses)
            if course_count.count >= 10:
                await self.award_badge(user_id, "consistency")
            
            # Check for other milestone badges
            if course_count.count >= 5:
                await self._check_and_award_high_achiever(user_id)
        
        except Exception as e:
            logger.error(f"Error awarding completion badges: {str(e)}")
    
    async def _award_exam_badges(self, user_id: str, percentage: float) -> None:
        """Award badges based on exam performance"""
        try:
            # Perfect score badge
            if percentage == 100:
                await self.award_badge(user_id, "perfect_score")
            
            # Check high achiever status
            if percentage >= 85:
                await self._check_and_award_high_achiever(user_id)
            
            # Check excellence status
            if percentage >= 90:
                await self._check_and_award_excellence(user_id)
        
        except Exception as e:
            logger.error(f"Error awarding exam badges: {str(e)}")
    
    async def _check_and_award_high_achiever(self, user_id: str) -> None:
        """Check and award high achiever badge"""
        try:
            # Get user's course completion stats
            certs = supabase_client.table("certificates").select(
                "percentage, score", count="exact"
            ).eq("user_id", user_id).gt("percentage", 84).execute()
            
            if certs.count >= 5:
                await self.award_badge(user_id, "high_achiever")
        
        except Exception as e:
            logger.error(f"Error checking high achiever badge: {str(e)}")
    
    async def _check_and_award_excellence(self, user_id: str) -> None:
        """Check and award excellence badge"""
        try:
            certs = supabase_client.table("certificates").select(
                "percentage", count="exact"
            ).eq("user_id", user_id).gt("percentage", 89).execute()
            
            if certs.count >= 20:
                await self.award_badge(user_id, "excellence")
        
        except Exception as e:
            logger.error(f"Error checking excellence badge: {str(e)}")
    
    async def award_badge(self, user_id: str, badge_key: str) -> Dict[str, Any]:
        """
        Award a badge to user
        
        Args:
            user_id: User ID
            badge_key: Badge identifier key
            
        Returns:
            Badge award record
        """
        try:
            if badge_key not in self.BADGES:
                raise ValueError(f"Badge {badge_key} not found")
            
            badge_def = self.BADGES[badge_key]
            
            # Check if user already has this badge
            existing = supabase_client.table("user_badges").select("*").eq(
                "user_id", user_id
            ).eq("badge_key", badge_key).execute()
            
            if existing.data:
                logger.info(f"User {user_id} already has badge {badge_key}")
                return {
                    "badge_id": existing.data[0]["id"],
                    "already_awarded": True
                }
            
            # Create badge award record
            badge_id = str(uuid.uuid4())
            badge_data = {
                "id": badge_id,
                "user_id": user_id,
                "badge_key": badge_key,
                "name": badge_def["name"],
                "description": badge_def["description"],
                "icon": badge_def["icon"],
                "category": badge_def["category"],
                "awarded_date": datetime.now(timezone.utc).isoformat(),
                "is_featured": False
            }
            
            result = supabase_client.table("user_badges").insert(badge_data).execute()
            
            logger.info(f"Badge {badge_key} awarded to user {user_id}")
            
            return {
                "badge_id": badge_id,
                "badge_key": badge_key,
                "name": badge_def["name"],
                "awarded_date": badge_data["awarded_date"]
            }
        
        except Exception as e:
            logger.error(f"Error awarding badge: {str(e)}")
            raise
    
    async def get_user_badges(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all badges earned by user
        
        Args:
            user_id: User ID
            
        Returns:
            List of user badges
        """
        try:
            result = supabase_client.table("user_badges").select("*").eq(
                "user_id", user_id
            ).order("awarded_date", desc=True).execute()
            
            return result.data or []
        
        except Exception as e:
            logger.error(f"Error fetching user badges: {str(e)}")
            raise
    
    async def get_user_achievements(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's complete achievement summary
        
        Args:
            user_id: User ID
            
        Returns:
            Achievement summary with certificates, badges, stats
        """
        try:
            # Get certificates
            certs_result = supabase_client.table("certificates").select(
                "id, certificate_number, title, issued_date, type, grade, percentage"
            ).eq("user_id", user_id).execute()
            
            certificates = certs_result.data or []
            
            # Get badges
            badges_result = supabase_client.table("user_badges").select(
                "id, badge_key, name, icon, awarded_date, category"
            ).eq("user_id", user_id).execute()
            
            badges = badges_result.data or []
            
            # Calculate stats
            course_certs = [c for c in certificates if c.get("type") == "course_completion"]
            exam_certs = [c for c in certificates if c.get("type") == "exam_completion"]
            
            avg_percentage = 0
            if exam_certs:
                total = sum(c.get("percentage", 0) for c in exam_certs)
                avg_percentage = total / len(exam_certs)
            
            return {
                "user_id": user_id,
                "total_certificates": len(certificates),
                "course_certificates": len(course_certs),
                "exam_certificates": len(exam_certs),
                "total_badges": len(badges),
                "average_exam_score": round(avg_percentage, 2),
                "certificates": certificates,
                "badges": badges,
                "badge_categories": {
                    "milestone": len([b for b in badges if b["category"] == "milestone"]),
                    "achievement": len([b for b in badges if b["category"] == "achievement"])
                }
            }
        
        except Exception as e:
            logger.error(f"Error fetching user achievements: {str(e)}")
            raise
    
    def verify_certificate(self, verification_code: str) -> Dict[str, Any]:
        """
        Verify a certificate by verification code
        
        Args:
            verification_code: Certificate verification code
            
        Returns:
            Verification result and certificate data
        """
        try:
            result = supabase_client.table("certificates").select(
                "*, users(full_name, email), courses(title), assessments(title)"
            ).eq("verification_code", verification_code).single().execute()
            
            if not result.data:
                return {
                    "valid": False,
                    "certificate": None,
                    "message": "Certificate not found"
                }
            
            certificate = result.data
            certificate["user_name"] = certificate.get("users", {}).get("full_name", "") if certificate.get("users") else ""
            certificate["user_email"] = certificate.get("users", {}).get("email", "") if certificate.get("users") else ""
            certificate["course_title"] = certificate.get("courses", {}).get("title", "") if certificate.get("courses") else ""
            certificate["assessment_title"] = certificate.get("assessments", {}).get("title", "") if certificate.get("assessments") else ""
            
            # Remove nested objects
            for key in ["users", "courses", "assessments"]:
                if key in certificate:
                    del certificate[key]
            
            return {
                "valid": True,
                "certificate": certificate,
                "message": "Certificate verified successfully"
            }
        
        except Exception as e:
            logger.error(f"Error verifying certificate: {str(e)}")
            raise
    
    def _calculate_grade(self, percentage: float) -> str:
        """Calculate letter grade based on percentage"""
        if percentage >= 95:
            return "A+"
        elif percentage >= 90:
            return "A"
        elif percentage >= 85:
            return "B+"
        elif percentage >= 80:
            return "B"
        elif percentage >= 75:
            return "C+"
        elif percentage >= 70:
            return "C"
        elif percentage >= 65:
            return "D+"
        elif percentage >= 60:
            return "D"
        else:
            return "F"


# Singleton instance
certificate_service = CertificateService()

