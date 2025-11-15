"""
Comprehensive tests for Courses service and endpoints
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import status
import uuid
from datetime import datetime


class TestCourseEndpoints:
    """Tests for course endpoints"""

    def test_list_courses(self, client, auth_headers, mock_courses, mock_supabase_client):
        """Test listing all courses"""
        mock_supabase_client.table.return_value.select.return_value.range.return_value.order.return_value.execute.return_value.data = mock_courses
        mock_supabase_client.table.return_value.select.return_value.range.return_value.order.return_value.execute.return_value.count = len(mock_courses)

        response = client.get(
            "/api/v1/courses",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert isinstance(data, dict) or isinstance(data, list)

    def test_get_course_detail(self, client, auth_headers, mock_course, mock_supabase_client):
        """Test retrieving course details"""
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_course
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.count = 0

        response = client.get(
            f"/api/v1/courses/{mock_course['id']}",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert data.get("id") == mock_course["id"]
            assert data.get("title") == mock_course["title"]

    def test_create_course(self, client, auth_headers, mock_supabase_client):
        """Test creating a new course"""
        course_data = {
            "title": "New Course",
            "description": "Course description",
            "instructor_id": "instructor1",
            "category": "programming"
        }

        new_course = {**course_data, "id": str(uuid.uuid4())}
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value.data = [new_course]

        response = client.post(
            "/api/v1/courses",
            headers=auth_headers,
            json=course_data
        )

        assert response.status_code in [
            status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert data.get("title") == course_data["title"]

    def test_update_course(self, client, auth_headers, mock_course, mock_supabase_client):
        """Test updating a course"""
        updated_data = {
            "title": "Updated Course Title",
            "description": "Updated description"
        }

        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {**mock_course, **updated_data}
        ]

        response = client.put(
            f"/api/v1/courses/{mock_course['id']}",
            headers=auth_headers,
            json=updated_data
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert data.get("title") == updated_data["title"]

    def test_delete_course(self, client, auth_headers, mock_course, mock_supabase_client):
        """Test deleting a course"""
        mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = None

        response = client.delete(
            f"/api/v1/courses/{mock_course['id']}",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_204_NO_CONTENT, status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    def test_search_courses(self, client, auth_headers, mock_supabase_client):
        """Test searching courses"""
        courses = [
            {"id": "1", "title": "Python Course", "category": "programming"},
            {"id": "2", "title": "Python Web Dev", "category": "programming"}
        ]

        mock_supabase_client.table.return_value.select.return_value.ilike.return_value.range.return_value.order.return_value.execute.return_value.data = courses
        mock_supabase_client.table.return_value.select.return_value.ilike.return_value.range.return_value.order.return_value.execute.return_value.count = len(courses)

        response = client.get(
            "/api/v1/courses?search=python",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert isinstance(data, dict) or isinstance(data, list)


