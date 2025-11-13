"""
Certificate and Badge Service Tests
Tests for certificate generation, badge awards, and achievement tracking
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.certificate_service import certificate_service
import uuid
from datetime import datetime


class TestCertificateGeneration:
    """Tests for certificate generation functionality"""
    
    @pytest.mark.asyncio
    async def test_generate_course_certificate_success(self):
        """Test successful course certificate generation"""
        with patch('app.services.certificate_service.supabase_client') as mock_sb:
            # Mock course data
            mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "id": "course-123",
                "title": "Python Basics",
                "duration_hours": 10,
                "instructor_id": "instructor-123"
            }
            
            # Mock existing certificate check
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = None
            
            # Mock progress data
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "completion_percentage": 100,
                "total_watch_time_minutes": 600
            }
            
            # Mock certificate insertion
            mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{}]
            
            result = await certificate_service.generate_course_completion_certificate(
                user_id="user-123",
                course_id="course-123"
            )
            
            assert "certificate_id" in result
            assert "certificate_number" in result
            assert result["certificate_number"].startswith("CERT-")
            assert "verification_code" in result
            assert result["verification_code"].startswith("VER-")
            assert "title" in result
            assert "issued_date" in result
    
    @pytest.mark.asyncio
    async def test_generate_exam_certificate_with_passing_score(self):
        """Test exam certificate generation with passing score"""
        with patch('app.services.certificate_service.supabase_client') as mock_sb:
            # Mock assessment data
            mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "id": "assessment-123",
                "title": "Python Final Exam",
                "course_id": "course-123",
                "total_points": 100
            }
            
            # Mock existing certificate check
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = None
            
            # Mock certificate insertion
            mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{}]
            
            result = await certificate_service.generate_exam_certificate(
                user_id="user-123",
                assessment_id="assessment-123",
                score=85,
                percentage=85
            )
            
            assert "certificate_id" in result
            assert "certificate_number" in result
            assert result["certificate_number"].startswith("EXAM-")
            assert "verification_code" in result
            assert "grade" in result
            assert result["grade"] in ["A+", "A", "B+", "B", "C+", "C", "D+", "D", "F"]
            assert result["percentage"] == 85
    
    @pytest.mark.asyncio
    async def test_generate_exam_certificate_below_passing_score(self):
        """Test exam certificate not generated for below passing score"""
        with patch('app.services.certificate_service.supabase_client') as mock_sb:
            # Mock assessment data
            mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "id": "assessment-123",
                "title": "Python Final Exam",
                "course_id": "course-123"
            }
            
            result = await certificate_service.generate_exam_certificate(
                user_id="user-123",
                assessment_id="assessment-123",
                score=50,
                percentage=50
            )
            
            assert "error" in result
            assert result["percentage"] == 50
    
    @pytest.mark.asyncio
    async def test_certificate_already_exists(self):
        """Test handling of duplicate certificate requests"""
        with patch('app.services.certificate_service.supabase_client') as mock_sb:
            # Mock course data
            mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "id": "course-123",
                "title": "Python Basics",
                "duration_hours": 10,
                "instructor_id": "instructor-123"
            }
            
            # Mock existing certificate
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {
                    "id": "cert-123",
                    "certificate_number": "CERT-20251115-ABC123",
                    "verification_code": "VER-abc-xyz"
                }
            ]
            
            result = await certificate_service.generate_course_completion_certificate(
                user_id="user-123",
                course_id="course-123"
            )
            
            assert result["already_exists"] == True
            assert result["certificate_id"] == "cert-123"
    
    def test_calculate_grade_boundaries(self):
        """Test grade calculation at boundaries"""
        test_cases = [
            (100, "A+"),
            (95, "A+"),
            (94, "A"),
            (90, "A"),
            (89, "B+"),
            (85, "B+"),
            (84, "B"),
            (80, "B"),
            (79, "C+"),
            (75, "C+"),
            (74, "C"),
            (70, "C"),
            (69, "D+"),
            (65, "D+"),
            (64, "D"),
            (60, "D"),
            (59, "F"),
            (0, "F")
        ]
        
        for percentage, expected_grade in test_cases:
            assert certificate_service._calculate_grade(percentage) == expected_grade
    
    def test_verify_certificate_success(self):
        """Test certificate verification"""
        with patch('app.services.certificate_service.supabase_client') as mock_sb:
            # Mock certificate data
            mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "id": "cert-123",
                "certificate_number": "CERT-20251115-ABC123",
                "verification_code": "VER-abc-xyz",
                "title": "Certificate of Completion",
                "type": "course_completion",
                "issued_date": "2025-11-15T10:30:00Z",
                "users": {"full_name": "John Doe", "email": "john@example.com"},
                "courses": {"title": "Python Basics"},
                "assessments": None,
                "is_verified": True
            }
            
            result = certificate_service.verify_certificate("VER-abc-xyz")
            
            assert result["valid"] == True
            assert result["certificate"]["certificate_number"] == "CERT-20251115-ABC123"
            assert result["certificate"]["user_name"] == "John Doe"
            assert result["certificate"]["course_title"] == "Python Basics"
    
    def test_verify_certificate_not_found(self):
        """Test certificate verification with invalid code"""
        with patch('app.services.certificate_service.supabase_client') as mock_sb:
            # Mock no certificate found
            mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None
            
            result = certificate_service.verify_certificate("INVALID-CODE")
            
            assert result["valid"] == False
            assert result["certificate"] is None


class TestBadgeAwards:
    """Tests for badge award functionality"""
    
    @pytest.mark.asyncio
    async def test_award_badge_success(self):
        """Test successful badge award"""
        with patch('app.services.certificate_service.supabase_client') as mock_sb:
            # Mock no existing badge
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = None
            
            # Mock badge insertion
            mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{}]
            
            result = await certificate_service.award_badge(
                user_id="user-123",
                badge_key="perfect_score"
            )
            
            assert "badge_id" in result
            assert result["badge_key"] == "perfect_score"
            assert result["name"] == "⭐ Perfect Score"
            assert "awarded_date" in result
    
    @pytest.mark.asyncio
    async def test_award_badge_already_awarded(self):
        """Test handling of duplicate badge awards"""
        with patch('app.services.certificate_service.supabase_client') as mock_sb:
            # Mock existing badge
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": "badge-123"}
            ]
            
            result = await certificate_service.award_badge(
                user_id="user-123",
                badge_key="perfect_score"
            )
            
            assert result["already_awarded"] == True
    
    @pytest.mark.asyncio
    async def test_award_badge_invalid_key(self):
        """Test badge award with invalid key"""
        with pytest.raises(ValueError):
            await certificate_service.award_badge(
                user_id="user-123",
                badge_key="invalid_badge_key"
            )
    
    @pytest.mark.asyncio
    async def test_get_user_badges(self):
        """Test retrieving user badges"""
        with patch('app.services.certificate_service.supabase_client') as mock_sb:
            # Mock badges
            mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                {
                    "id": "badge-1",
                    "badge_key": "first_course",
                    "name": "🎓 First Course",
                    "awarded_date": "2025-11-01T10:00:00Z"
                },
                {
                    "id": "badge-2",
                    "badge_key": "perfect_score",
                    "name": "⭐ Perfect Score",
                    "awarded_date": "2025-11-15T10:00:00Z"
                }
            ]
            
            result = await certificate_service.get_user_badges("user-123")
            
            assert len(result) == 2
            assert result[0]["badge_key"] == "first_course"
            assert result[1]["badge_key"] == "perfect_score"


class TestAchievementTracking:
    """Tests for achievement tracking and statistics"""
    
    @pytest.mark.asyncio
    async def test_get_user_achievements(self):
        """Test retrieving user achievement summary"""
        with patch('app.services.certificate_service.supabase_client') as mock_sb:
            # Mock certificates
            mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                {
                    "id": "cert-1",
                    "certificate_number": "CERT-1",
                    "title": "Course 1",
                    "type": "course_completion",
                    "issued_date": "2025-11-01T10:00:00Z"
                },
                {
                    "id": "cert-2",
                    "certificate_number": "EXAM-1",
                    "title": "Exam 1",
                    "type": "exam_completion",
                    "issued_date": "2025-11-15T10:00:00Z",
                    "percentage": 95
                }
            ]
            
            # Mock badges
            mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                {
                    "id": "badge-1",
                    "badge_key": "perfect_score",
                    "name": "⭐ Perfect Score",
                    "category": "achievement"
                }
            ]
            
            result = await certificate_service.get_user_achievements("user-123")
            
            assert result["total_certificates"] >= 1
            assert "course_certificates" in result
            assert "exam_certificates" in result
            assert "total_badges" in result
            assert "average_exam_score" in result
            assert "certificates" in result
            assert "badges" in result


class TestCompletionBadges:
    """Tests for completion-based badge awards"""
    
    @pytest.mark.asyncio
    async def test_first_course_badge_award(self):
        """Test first course badge is awarded"""
        with patch('app.services.certificate_service.supabase_client') as mock_sb:
            # Mock course completion count (first course = 0 before)
            mock_execute = MagicMock()
            mock_execute.count = 0
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_execute
            
            # Mock badge insertion
            with patch.object(certificate_service, 'award_badge', new_callable=AsyncMock) as mock_award:
                await certificate_service._award_completion_badges("user-123", "course-123")
                mock_award.assert_called_with("user-123", "first_course")


class TestBadgeDefinitions:
    """Tests for badge definitions"""
    
    def test_all_badges_have_required_fields(self):
        """Test that all badges have required fields"""
        required_fields = ["name", "description", "icon", "category", "criteria"]
        
        for badge_key, badge_def in certificate_service.BADGES.items():
            for field in required_fields:
                assert field in badge_def, f"Badge {badge_key} missing field {field}"
    
    def test_badge_categories_are_valid(self):
        """Test badge categories are valid"""
        valid_categories = {"milestone", "achievement"}
        
        for badge_key, badge_def in certificate_service.BADGES.items():
            assert badge_def["category"] in valid_categories
    
    def test_badge_criteria_types(self):
        """Test badge criteria types are documented"""
        valid_criteria_types = {
            "first_completion",
            "exam_score",
            "multiple_courses",
            "course_count",
            "fast_completion",
            "watch_time",
            "specialization_complete"
        }
        
        for badge_key, badge_def in certificate_service.BADGES.items():
            assert badge_def["criteria"]["type"] in valid_criteria_types


class TestIntegration:
    """Integration tests for certificate and badge system"""
    
    @pytest.mark.asyncio
    async def test_complete_course_flow(self):
        """Test complete course completion flow"""
        # This would be an integration test with real database
        pass
    
    @pytest.mark.asyncio
    async def test_complete_exam_flow(self):
        """Test complete exam completion flow"""
        # This would be an integration test with real database
        pass
    
    @pytest.mark.asyncio
    async def test_badge_progression_flow(self):
        """Test complete badge progression"""
        # This would be an integration test with real database
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
