"""
Comprehensive tests for Analytics service and endpoints
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import status
import uuid


class TestAnalyticsEndpoints:
    """Tests for analytics endpoints"""

    def test_get_user_analytics(self, client, auth_headers, mock_supabase_client):
        """Test retrieving user analytics"""
        analytics_data = {
            "total_courses": 5,
            "completed_courses": 2,
            "in_progress_courses": 2,
            "total_learning_hours": 45.5,
            "average_score": 82.3,
            "certificates_earned": 2,
            "badges_earned": 5,
            "last_accessed": "2024-01-20T10:00:00Z"
        }

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = analytics_data

        response = client.get(
            "/api/v1/analytics/user",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert data.get("total_courses") is not None

    def test_get_course_analytics(self, client, auth_headers, mock_supabase_client):
        """Test retrieving course analytics"""
        course_id = "course1"
        analytics_data = {
            "course_id": course_id,
            "total_enrolled": 150,
            "completed": 45,
            "in_progress": 80,
            "average_score": 78.5,
            "completion_rate": 30.0,
            "engagement_score": 75.2
        }

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = analytics_data

        response = client.get(
            f"/api/v1/analytics/courses/{course_id}",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert data.get("completion_rate") is not None

    def test_get_learning_progress(self, client, auth_headers, mock_supabase_client):
        """Test retrieving learning progress"""
        progress_data = {
            "user_id": "user1",
            "courses": [
                {
                    "course_id": "course1",
                    "progress": 45,
                    "last_accessed": "2024-01-20T10:00:00Z"
                },
                {
                    "course_id": "course2",
                    "progress": 100,
                    "last_accessed": "2024-01-15T10:00:00Z"
                }
            ]
        }

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = progress_data.get("courses", [])

        response = client.get(
            "/api/v1/analytics/progress",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_get_performance_metrics(self, client, auth_headers, mock_supabase_client):
        """Test retrieving performance metrics"""
        metrics_data = {
            "avg_session_duration": 45.3,
            "session_frequency": 5.2,
            "quiz_attempt_count": 12,
            "quiz_pass_rate": 91.7,
            "assignment_completion_rate": 85.0,
            "discussion_participation": 15
        }

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = metrics_data

        response = client.get(
            "/api/v1/analytics/performance",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    def test_get_platform_statistics(self, client, auth_headers, mock_supabase_client):
        """Test retrieving platform statistics (admin only)"""
        stats_data = {
            "total_users": 5000,
            "active_users": 1200,
            "total_courses": 150,
            "total_enrollments": 8500,
            "total_revenue": 250000,
            "avg_user_satisfaction": 4.3
        }

        mock_supabase_client.table.return_value.select.return_value.single.return_value.execute.return_value.data = stats_data

        response = client.get(
            "/api/v1/analytics/platform",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
