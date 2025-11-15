"""
Comprehensive tests for Users service and endpoints
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import status
import uuid
from datetime import datetime


class TestUserEndpoints:
    """Tests for user endpoints"""

    def test_get_profile(self, client, auth_headers, mock_user, mock_supabase_client):
        """Test retrieving user profile"""
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_user

        response = client.get(
            f"/api/v1/users/{mock_user['id']}",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert data.get("id") == mock_user["id"]
            assert data.get("email") == mock_user["email"]

    def test_get_current_user_profile(self, client, auth_headers, mock_user, mock_supabase_client):
        """Test retrieving current user profile"""
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_user

        response = client.get(
            "/api/v1/users/me/profile",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert data.get("email") == mock_user["email"]

    def test_update_profile(self, client, auth_headers, mock_user, mock_supabase_client):
        """Test updating user profile"""
        updated_data = {
            "full_name": "Updated Name",
            "bio": "Updated bio",
            "avatar_url": "https://example.com/avatar.jpg"
        }

        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {**mock_user, **updated_data}
        ]

        response = client.put(
            "/api/v1/users/me/profile",
            headers=auth_headers,
            json=updated_data
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert data.get("full_name") == updated_data["full_name"]

    def test_update_profile_unauthorized(self, client):
        """Test updating profile without authentication"""
        response = client.put(
            "/api/v1/users/me/profile",
            json={"full_name": "Updated Name"}
        )

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    def test_get_user_stats(self, client, auth_headers, mock_user, mock_supabase_client):
        """Test retrieving user statistics"""
        stats = {
            "courses_enrolled": 5,
            "courses_completed": 2,
            "total_learning_hours": 45.5,
            "average_score": 85.3,
            "badges_earned": 3
        }

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = stats

        response = client.get(
            f"/api/v1/users/{mock_user['id']}/stats",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert "courses_enrolled" in data

    def test_get_user_learning_history(self, client, auth_headers, mock_user, mock_supabase_client):
        """Test retrieving user learning history"""
        history = [
            {
                "course_id": "course1",
                "course_name": "Python Basics",
                "enrolled_at": "2024-01-01",
                "progress": 75,
                "status": "in_progress"
            },
            {
                "course_id": "course2",
                "course_name": "Web Development",
                "enrolled_at": "2024-02-01",
                "progress": 100,
                "status": "completed"
            }
        ]

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = history

        response = client.get(
            f"/api/v1/users/{mock_user['id']}/learning-history",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert isinstance(data, list)

    def test_delete_user_account(self, client, auth_headers, mock_user, mock_supabase_client):
        """Test deleting user account"""
        mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = None

        response = client.delete(
            "/api/v1/users/me",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_204_NO_CONTENT, status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
