"""
Pytest configuration and fixtures for backend tests
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
import uuid
from starlette.testclient import TestClient
from app.main import app
from app.core.security import create_access_token, create_refresh_token


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock user data"""
    return {
        "id": str(uuid.uuid4()),
        "auth_id": str(uuid.uuid4()),
        "email": "testuser@example.com",
        "full_name": "Test User",
        "phone": "+919876543210",
        "role": "student",
        "email_verified": True,
        "phone_verified": True,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_instructor():
    """Mock instructor data"""
    return {
        "id": str(uuid.uuid4()),
        "auth_id": str(uuid.uuid4()),
        "email": "instructor@example.com",
        "full_name": "Test Instructor",
        "phone": "+919876543211",
        "role": "instructor",
        "email_verified": True,
        "phone_verified": True,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_admin():
    """Mock admin data"""
    return {
        "id": str(uuid.uuid4()),
        "auth_id": str(uuid.uuid4()),
        "email": "admin@example.com",
        "full_name": "Test Admin",
        "phone": "+919876543212",
        "role": "admin",
        "email_verified": True,
        "phone_verified": True,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def auth_headers(mock_user):
    """Generate auth headers with valid token"""
    token = create_access_token({"sub": mock_user["id"], "role": mock_user["role"]})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def instructor_auth_headers(mock_instructor):
    """Generate auth headers for instructor"""
    token = create_access_token({"sub": mock_instructor["id"], "role": mock_instructor["role"]})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(mock_admin):
    """Generate auth headers for admin"""
    token = create_access_token({"sub": mock_admin["id"], "role": mock_admin["role"]})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_course():
    """Mock course data"""
    instructor_id = str(uuid.uuid4())
    return {
        "id": str(uuid.uuid4()),
        "title": "Python Basics",
        "description": "Learn Python programming from scratch",
        "instructor_id": instructor_id,
        "category": "programming",
        "level": "beginner",
        "duration_hours": 10,
        "thumbnail_url": "https://example.com/thumbnail.jpg",
        "price": 99.99,
        "is_published": True,
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_module():
    """Mock course module"""
    course_id = str(uuid.uuid4())
    return {
        "id": str(uuid.uuid4()),
        "course_id": course_id,
        "title": "Module 1: Basics",
        "description": "Introduction to Python",
        "order": 1,
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_content():
    """Mock content item"""
    module_id = str(uuid.uuid4())
    return {
        "id": str(uuid.uuid4()),
        "module_id": module_id,
        "title": "Video: Introduction",
        "type": "video",
        "video_url": "https://example.com/video.mp4",
        "duration_seconds": 600,
        "order": 1,
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_assessment():
    """Mock assessment"""
    course_id = str(uuid.uuid4())
    module_id = str(uuid.uuid4())
    return {
        "id": str(uuid.uuid4()),
        "course_id": course_id,
        "module_id": module_id,
        "title": "Quiz 1",
        "description": "Assessment for Module 1",
        "type": "quiz",
        "total_points": 100,
        "passing_score": 60,
        "is_published": True,
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_question():
    """Mock question"""
    assessment_id = str(uuid.uuid4())
    return {
        "id": str(uuid.uuid4()),
        "assessment_id": assessment_id,
        "question_text": "What is Python?",
        "question_type": "multiple_choice",
        "points": 10,
        "order": 1,
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_enrollment():
    """Mock enrollment"""
    user_id = str(uuid.uuid4())
    course_id = str(uuid.uuid4())
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "course_id": course_id,
        "status": "active",
        "progress_percentage": 0,
        "enrolled_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_certificate():
    """Mock certificate"""
    user_id = str(uuid.uuid4())
    course_id = str(uuid.uuid4())
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "course_id": course_id,
        "type": "course_completion",
        "certificate_number": "CERT-20251114-ABC123",
        "verification_code": "VER-abc-xyz",
        "issued_date": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_payment_order():
    """Mock payment order"""
    user_id = str(uuid.uuid4())
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "amount": 99.99,
        "currency": "INR",
        "status": "pending",
        "payment_method": "card",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_proctoring_session():
    """Mock proctoring session"""
    user_id = str(uuid.uuid4())
    attempt_id = str(uuid.uuid4())
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "attempt_id": attempt_id,
        "status": "active",
        "start_time": datetime.utcnow().isoformat(),
        "end_time": None,
    }


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client - simpler approach"""
    mock_client = MagicMock()
    
    # Setup auth mock
    mock_auth_user = MagicMock()
    mock_auth_user.id = str(uuid.uuid4())
    mock_client.auth.sign_in_with_password.return_value.user = mock_auth_user
    
    # Setup table select mock chain
    mock_table = MagicMock()
    mock_exec_response = MagicMock()
    mock_exec_response.data = [
        {
            "id": "mock-user-id",
            "auth_id": "mock-auth-id",
            "email": "testuser@example.com",
            "full_name": "Test User",
            "phone": "+919876543210",
            "role": "student",
            "email_verified": True,
            "phone_verified": True,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
        }
    ]
    
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_exec_response
    mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_exec_response
    mock_table.insert.return_value.execute.return_value.data = [
        {
            "id": str(uuid.uuid4()),
            "auth_id": "mock-auth-id",
            "email": "newuser@example.com",
            "full_name": "New User",
            "role": "student",
        }
    ]
    
    mock_client.table.return_value = mock_table
    
    with patch('app.core.supabase_client.supabase_client', mock_client):
        yield mock_client


@pytest.fixture
def mock_supabase_admin():
    """Mock Supabase admin client"""
    mock_admin = MagicMock()
    mock_auth_user = MagicMock()
    mock_auth_user.id = str(uuid.uuid4())
    mock_admin.auth.admin.create_user.return_value.user = mock_auth_user
    mock_admin.auth.admin.update_user_by_id.return_value = None
    
    with patch('app.core.supabase_client.supabase_admin', mock_admin):
        yield mock_admin


@pytest.fixture
def mock_courses():
    """Mock courses list for testing"""
    return [
        {
            "id": str(uuid.uuid4()),
            "title": "Introduction to Python",
            "category": "programming",
            "level": "beginner",
            "price": 99.99
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Web Development Basics",
            "category": "web",
            "level": "beginner",
            "price": 79.99
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Advanced Python",
            "category": "programming",
            "level": "advanced",
            "price": 149.99
        }
    ]


@pytest.fixture
def mock_assessments():
    """Mock assessments list for testing"""
    return [
        {
            "id": str(uuid.uuid4()),
            "course_id": str(uuid.uuid4()),
            "title": "Quiz 1",
            "type": "quiz",
            "duration_minutes": 60
        },
        {
            "id": str(uuid.uuid4()),
            "course_id": str(uuid.uuid4()),
            "title": "Midterm Exam",
            "type": "exam",
            "duration_minutes": 120
        }
    ]


@pytest.fixture
def mock_content_items():
    """Mock content items list for testing"""
    course_id = str(uuid.uuid4())
    return [
        {
            "id": str(uuid.uuid4()),
            "course_id": course_id,
            "title": "Lesson 1: Basics",
            "content_type": "video",
            "duration_seconds": 1200,
            "order": 1
        },
        {
            "id": str(uuid.uuid4()),
            "course_id": course_id,
            "title": "Lesson 2: Advanced",
            "content_type": "video",
            "duration_seconds": 1800,
            "order": 2
        },
        {
            "id": str(uuid.uuid4()),
            "course_id": course_id,
            "title": "Reading: Resources",
            "content_type": "document",
            "order": 3
        }
    ]
