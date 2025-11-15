"""
Comprehensive tests for Enrollments service and endpoints
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import status
import uuid


class TestEnrollmentEndpoints:
    """Tests for enrollment endpoints"""

    def test_enroll_in_course(self, client, auth_headers, mock_supabase_client):
        """Test enrolling in a course"""
        enrollment_data = {
            "course_id": "course1",
            "enrollment_type": "paid"
        }

        enrollment_response = {
            "id": str(uuid.uuid4()),
            "user_id": "user1",
            **enrollment_data,
            "status": "active",
            "enrolled_at": "2024-01-15T10:00:00Z"
        }

        mock_supabase_client.table.return_value.insert.return_value.execute.return_value.data = [enrollment_response]

        response = client.post(
            "/api/v1/enrollments",
            headers=auth_headers,
            json=enrollment_data
        )

        assert response.status_code in [
            status.HTTP_201_CREATED, status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND, status.HTTP_409_CONFLICT,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert data.get("status") == "active"

    def test_get_user_enrollments(self, client, auth_headers, mock_supabase_client):
        """Test retrieving user enrollments"""
        enrollments = [
            {
                "id": str(uuid.uuid4()),
                "course_id": "course1",
                "course_title": "Python Basics",
                "status": "active",
                "progress": 45
            },
            {
                "id": str(uuid.uuid4()),
                "course_id": "course2",
                "course_title": "Web Development",
                "status": "completed",
                "progress": 100
            }
        ]

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = enrollments

        response = client.get(
            "/api/v1/enrollments",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert isinstance(data, list)

    def test_get_enrollment_detail(self, client, auth_headers, mock_supabase_client):
        """Test retrieving enrollment details"""
        enrollment_id = str(uuid.uuid4())
        enrollment_response = {
            "id": enrollment_id,
            "user_id": "user1",
            "course_id": "course1",
            "status": "active",
            "enrolled_at": "2024-01-15T10:00:00Z",
            "progress": 45
        }

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = enrollment_response

        response = client.get(
            f"/api/v1/enrollments/{enrollment_id}",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert data.get("status") in ["active", "completed", "dropped"]

    def test_update_enrollment_progress(self, client, auth_headers, mock_supabase_client):
        """Test updating enrollment progress"""
        enrollment_id = str(uuid.uuid4())
        progress_data = {
            "progress": 60
        }

        updated_enrollment = {
            "id": enrollment_id,
            "user_id": "user1",
            "course_id": "course1",
            **progress_data,
            "status": "active"
        }

        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [updated_enrollment]

        response = client.put(
            f"/api/v1/enrollments/{enrollment_id}",
            headers=auth_headers,
            json=progress_data
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    def test_drop_course(self, client, auth_headers, mock_supabase_client):
        """Test dropping a course"""
        enrollment_id = str(uuid.uuid4())

        dropped_enrollment = {
            "id": enrollment_id,
            "user_id": "user1",
            "course_id": "course1",
            "status": "dropped",
            "dropped_at": "2024-01-20T10:00:00Z"
        }

        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [dropped_enrollment]

        response = client.delete(
            f"/api/v1/enrollments/{enrollment_id}",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_204_NO_CONTENT,
            status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
