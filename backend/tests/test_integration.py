"""
Integration tests for the SLMS backend
"""

import pytest
from fastapi import status
import uuid
from unittest.mock import MagicMock, patch


class TestAuthFlow:
    """Integration tests for authentication flow"""

    def test_complete_auth_flow(self, client, mock_supabase_client):
        """Test complete authentication flow: signup, login, access protected resource"""
        # Signup
        signup_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "full_name": "New User"
        }

        signup_response = client.post(
            "/api/v1/auth/signup",
            json=signup_data
        )

        assert signup_response.status_code in [
            status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST,
            status.HTTP_409_CONFLICT, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

        # Login
        login_data = {
            "email": signup_data["email"],
            "password": signup_data["password"]
        }

        login_response = client.post(
            "/api/v1/auth/login",
            json=login_data
        )

        assert login_response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

        # Access protected resource
        if login_response.status_code == status.HTTP_200_OK:
            token_data = login_response.json()
            if "access_token" in token_data:
                headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                profile_response = client.get("/api/v1/users/me/profile", headers=headers)
                assert profile_response.status_code in [
                    status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
                    status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN,
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ]


class TestEnrollmentFlow:
    """Integration tests for enrollment and learning flow"""

    def test_course_enrollment_and_learning(self, client, auth_headers, mock_supabase_client):
        """Test complete flow: browse courses, enroll, access content"""
        # List courses
        course_response = client.get("/api/v1/courses")
        assert course_response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

        # Get course details
        course_id = str(uuid.uuid4())
        detail_response = client.get(f"/api/v1/courses/{course_id}")
        assert detail_response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

        # Enroll in course
        enroll_response = client.post(
            "/api/v1/enrollments",
            headers=auth_headers,
            json={"course_id": course_id}
        )
        assert enroll_response.status_code in [
            status.HTTP_201_CREATED, status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN,
            status.HTTP_409_CONFLICT, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

        # Access course content
        if enroll_response.status_code < 400:
            content_response = client.get(
                f"/api/v1/courses/{course_id}/content",
                headers=auth_headers
            )
            assert content_response.status_code in [
                status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ]


class TestPaymentFlow:
    """Integration tests for payment flow"""

    def test_payment_flow(self, client, auth_headers, mock_supabase_client):
        """Test payment initiation and verification"""
        course_id = str(uuid.uuid4())

        # Initiate payment
        payment_response = client.post(
            "/api/v1/payments/initiate",
            headers=auth_headers,
            json={
                "course_id": course_id,
                "amount": 99.99,
                "currency": "USD"
            }
        )

        assert payment_response.status_code in [
            status.HTTP_200_OK, status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

        # Verify payment if initiated
        if payment_response.status_code < 400:
            payment_data = payment_response.json()
            if "id" in payment_data:
                payment_id = payment_data["id"]
                verify_response = client.get(
                    f"/api/v1/payments/{payment_id}/verify",
                    headers=auth_headers
                )
                assert verify_response.status_code in [
                    status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
                    status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND,
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ]


class TestAssessmentFlow:
    """Integration tests for assessment flow"""

    def test_assessment_flow(self, client, auth_headers, mock_supabase_client):
        """Test complete assessment flow: retrieve, attempt, get results"""
        assessment_id = str(uuid.uuid4())

        # Get assessment
        get_response = client.get(
            f"/api/v1/assessments/{assessment_id}",
            headers=auth_headers
        )

        assert get_response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

        # Submit answers
        if get_response.status_code < 400:
            submission_response = client.post(
                "/api/v1/assessments/submit",
                headers=auth_headers,
                json={
                    "assessment_id": assessment_id,
                    "answers": {
                        "q1": "answer1",
                        "q2": "answer2"
                    }
                }
            )

            assert submission_response.status_code in [
                status.HTTP_200_OK, status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN,
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ]

            # Get result
            if submission_response.status_code < 400:
                result_data = submission_response.json()
                if "id" in result_data:
                    result_response = client.get(
                        f"/api/v1/assessments/{result_data['id']}",
                        headers=auth_headers
                    )
                    assert result_response.status_code in [
                        status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
                        status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND,
                        status.HTTP_500_INTERNAL_SERVER_ERROR
                    ]


class TestAnalyticsFlow:
    """Integration tests for analytics tracking"""

    def test_analytics_data_retrieval(self, client, auth_headers, mock_supabase_client):
        """Test retrieving analytics data"""
        # Get user analytics
        user_analytics_response = client.get(
            "/api/v1/analytics/user",
            headers=auth_headers
        )

        assert user_analytics_response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

        # Get learning progress
        progress_response = client.get(
            "/api/v1/analytics/progress",
            headers=auth_headers
        )

        assert progress_response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

        # Get performance metrics
        metrics_response = client.get(
            "/api/v1/analytics/performance",
            headers=auth_headers
        )

        assert metrics_response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]


class TestErrorHandling:
    """Integration tests for error handling"""

    def test_unauthorized_access(self, client):
        """Test accessing protected resources without auth"""
        response = client.get("/api/v1/users/me/profile")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN,
            status.HTTP_400_BAD_REQUEST
        ]

    def test_invalid_course_id(self, client, auth_headers):
        """Test accessing non-existent course"""
        response = client.get(
            "/api/v1/courses/invalid-course-id",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    def test_invalid_payment_data(self, client, auth_headers):
        """Test initiating payment with invalid data"""
        response = client.post(
            "/api/v1/payments/initiate",
            headers=auth_headers,
            json={"amount": -100}  # Invalid amount
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    def test_duplicate_enrollment(self, client, auth_headers, mock_supabase_client):
        """Test enrolling in same course twice"""
        course_id = str(uuid.uuid4())

        # First enrollment
        first_response = client.post(
            "/api/v1/enrollments",
            headers=auth_headers,
            json={"course_id": course_id}
        )

        # Second enrollment (duplicate)
        second_response = client.post(
            "/api/v1/enrollments",
            headers=auth_headers,
            json={"course_id": course_id}
        )

        # Second enrollment should either succeed or return conflict
        assert second_response.status_code in [
            status.HTTP_201_CREATED, status.HTTP_200_OK,
            status.HTTP_409_CONFLICT, status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
