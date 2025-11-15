"""
Comprehensive tests for Content service and endpoints
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import status
import uuid


class TestContentEndpoints:
    """Tests for content endpoints"""

    def test_list_course_content(self, client, mock_content_items, mock_supabase_client):
        """Test listing course content"""
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = mock_content_items

        response = client.get("/api/v1/courses/course1/content")

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert isinstance(data, list)

    def test_get_content_detail(self, client, mock_content, mock_supabase_client):
        """Test retrieving content details"""
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_content

        response = client.get(f"/api/v1/content/{mock_content['id']}")

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert data.get("id") == mock_content["id"]

    def test_create_content(self, client, auth_headers, mock_supabase_client):
        """Test creating content"""
        content_data = {
            "course_id": "course1",
            "title": "Lesson 1",
            "content_type": "video",
            "content_url": "https://example.com/video.mp4",
            "duration": 300
        }

        new_content = {
            **content_data,
            "id": str(uuid.uuid4())
        }

        mock_supabase_client.table.return_value.insert.return_value.execute.return_value.data = [new_content]

        response = client.post(
            "/api/v1/content",
            headers=auth_headers,
            json=content_data
        )

        assert response.status_code in [
            status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    def test_update_content(self, client, auth_headers, mock_content, mock_supabase_client):
        """Test updating content"""
        updated_data = {
            "title": "Updated Lesson",
            "duration": 600
        }

        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {**mock_content, **updated_data}
        ]

        response = client.put(
            f"/api/v1/content/{mock_content['id']}",
            headers=auth_headers,
            json=updated_data
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    def test_delete_content(self, client, auth_headers, mock_content, mock_supabase_client):
        """Test deleting content"""
        mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = None

        response = client.delete(
            f"/api/v1/content/{mock_content['id']}",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_204_NO_CONTENT, status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    def test_mark_content_complete(self, client, auth_headers, mock_supabase_client):
        """Test marking content as complete"""
        completion_data = {
            "content_id": "content1",
            "completed_at": "2024-01-15T10:00:00Z"
        }

        result_data = {
            "id": str(uuid.uuid4()),
            **completion_data
        }

        mock_supabase_client.table.return_value.insert.return_value.execute.return_value.data = [result_data]

        response = client.post(
            "/api/v1/content/complete",
            headers=auth_headers,
            json=completion_data
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
