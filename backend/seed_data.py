#!/usr/bin/env python3
"""
Sample Data Seeder for Smart LMS
Creates demo users, courses, and assessments for testing
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.supabase_client import supabase_client, supabase_admin
from app.core.security import get_password_hash

# Use admin client for seeding (bypasses RLS)
if not supabase_admin:
    print("❌ ERROR: SUPABASE_SERVICE_ROLE_KEY is not set. Cannot seed data.")
    sys.exit(1)

# Use admin client for all database operations in seeding
db = supabase_admin


def create_sample_users():
    """Create sample users"""
    print("\n👥 Creating sample users...")
    
    users = [
        {
            "email": "admin@smartlms.com",
            "password": "Admin123!",
            "full_name": "Admin User",
            "role": "admin"
        },
        {
            "email": "instructor@smartlms.com",
            "password": "Instructor123!",
            "full_name": "Dr. Sarah Johnson",
            "role": "instructor",
            "bio": "PhD in Computer Science, 10+ years teaching experience"
        },
        {
            "email": "student1@smartlms.com",
            "password": "Student123!",
            "full_name": "John Smith",
            "role": "student"
        },
        {
            "email": "student2@smartlms.com",
            "password": "Student123!",
            "full_name": "Emily Davis",
            "role": "student"
        }
    ]
    
    created_users = {}
    
    for user_data in users:
        try:
            # Check if user exists
            existing = db.table("users").select("id").eq("email", user_data["email"]).execute()
            
            if existing.data:
                print(f"   ⚠️  User {user_data['email']} already exists")
                created_users[user_data["role"]] = existing.data[0]["id"]
                continue
            
            # Create user profile
            user_profile = {
                "email": user_data["email"],
                "full_name": user_data["full_name"],
                "role": user_data["role"],
                "bio": user_data.get("bio"),
                "email_verified": True,
                "is_active": True
            }
            
            result = db.table("users").insert(user_profile).execute()
            user_id = result.data[0]["id"]
            created_users[user_data["role"]] = user_id
            
            print(f"   ✅ Created {user_data['role']}: {user_data['email']}")
            print(f"      Password: {user_data['password']}")
            
        except Exception as e:
            print(f"   ❌ Error creating {user_data['email']}: {e}")
    
    return created_users


def create_sample_courses(instructor_id):
    """Create sample courses"""
    print("\n📚 Creating sample courses...")
    
    courses = [
        {
            "title": "Introduction to Python Programming",
            "description": "Learn Python from scratch with hands-on projects. Perfect for beginners!",
            "instructor_id": instructor_id,
            "is_published": True,
            "enrollment_open": True
        },
        {
            "title": "Web Development with React",
            "description": "Build modern web applications with React.js, hooks, and best practices.",
            "instructor_id": instructor_id,
            "is_published": True,
            "enrollment_open": True
        },
        {
            "title": "Data Science Fundamentals",
            "description": "Master data analysis, visualization, and machine learning basics.",
            "instructor_id": instructor_id,
            "is_published": True,
            "enrollment_open": True
        }
    ]
    
    created_courses = []
    
    for course_data in courses:
        try:
            result = db.table("courses").insert(course_data).execute()
            course_id = result.data[0]["id"]
            created_courses.append({**result.data[0], "modules": []})
            print(f"   ✅ Created course: {course_data['title']}")
        except Exception as e:
            print(f"   ❌ Error creating course {course_data['title']}: {e}")
    
    return created_courses


def create_course_modules(courses):
    """Create modules for courses"""
    print("\n📖 Creating course modules...")
    
    for course in courses:
        modules_data = [
            {
                "course_id": course["id"],
                "title": "Getting Started",
                "description": "Introduction and setup",
                "order_index": 0
            },
            {
                "course_id": course["id"],
                "title": "Core Concepts",
                "description": "Learn the fundamentals",
                "order_index": 1
            },
            {
                "course_id": course["id"],
                "title": "Advanced Topics",
                "description": "Deep dive into advanced concepts",
                "order_index": 2
            }
        ]
        
        try:
            result = db.table("course_modules").insert(modules_data).execute()
            course["modules"] = result.data
            print(f"   ✅ Created modules for: {course['title']}")
        except Exception as e:
            print(f"   ❌ Error creating modules: {e}")
    
    return courses


def create_sample_assessments(courses):
    """Create sample assessments"""
    print("\n📝 Creating sample assessments...")
    
    for course in courses:
        if not course["modules"]:
            continue
        
        # Create a quiz
        assessment_data = {
            "course_id": course["id"],
            "module_id": course["modules"][0]["id"],
            "title": f"{course['title']} - Quiz 1",
            "description": "Test your knowledge of the basics",
            "assessment_type": "quiz",
            "duration": 30,
            "total_marks": 10.0,
            "passing_marks": 6.0,
            "proctoring_enabled": False,
            "max_attempts": 3,
            "show_results_immediately": True
        }
        
        try:
            result = db.table("assessments").insert(assessment_data).execute()
            assessment_id = result.data[0]["id"]
            
            # Create questions
            questions = [
                {
                    "assessment_id": assessment_id,
                    "question_text": "What is the main purpose of this course?",
                    "question_type": "mcq",
                    "marks": 2.0,
                    "order_index": 0
                },
                {
                    "assessment_id": assessment_id,
                    "question_text": "True or False: This is an advanced level course.",
                    "question_type": "true_false",
                    "marks": 2.0,
                    "order_index": 1
                }
            ]
            
            db.table("questions").insert(questions).execute()
            
            print(f"   ✅ Created assessment for: {course['title']}")
            
        except Exception as e:
            print(f"   ❌ Error creating assessment: {e}")
        
        # Create a proctored exam
        exam_data = {
            "course_id": course["id"],
            "title": f"{course['title']} - Final Exam",
            "description": "Comprehensive final examination with AI proctoring",
            "assessment_type": "exam",
            "duration": 60,
            "total_marks": 100.0,
            "passing_marks": 60.0,
            "proctoring_enabled": True,
            "proctoring_sensitivity": "high",
            "max_attempts": 1,
            "show_results_immediately": False
        }
        
        try:
            result = db.table("assessments").insert(exam_data).execute()
            print(f"   ✅ Created proctored exam for: {course['title']}")
        except Exception as e:
            print(f"   ❌ Error creating exam: {e}")


def enroll_students(courses, student_ids):
    """Enroll students in courses"""
    print("\n🎓 Enrolling students...")
    
    for student_id in student_ids:
        for course in courses[:2]:  # Enroll in first 2 courses
            enrollment_data = {
                "user_id": student_id,
                "course_id": course["id"],
                "status": "active"
            }
            
            try:
                result = db.table("enrollments").insert(enrollment_data).execute()
                print(f"   ✅ Enrolled student in: {course['title']}")
            except Exception as e:
                print(f"   ⚠️  Student may already be enrolled: {course['title']}")


def main():
    """Main seeding function"""
    print("="*60)
    print("🌱 Smart LMS - Sample Data Seeder")
    print("="*60)
    
    print("\n⚠️  WARNING: This will create sample data in your database.")
    response = input("Continue? (y/N): ")
    
    if response.lower() != 'y':
        print("❌ Seeding cancelled")
        return
    
    try:
        # Create users
        users = create_sample_users()
        
        if "instructor" not in users:
            print("\n❌ Error: Could not create instructor user")
            return
        
        # Create courses
        courses = create_sample_courses(users["instructor"])
        
        # Create modules
        courses = create_course_modules(courses)
        
        # Create assessments
        create_sample_assessments(courses)
        
        # Enroll students
        student_ids = [users.get("student"), users.get("student2")]
        student_ids = [sid for sid in student_ids if sid]  # Filter None values
        
        if student_ids:
            enroll_students(courses, student_ids)
        
        print("\n" + "="*60)
        print("✅ Sample data created successfully!")
        print("="*60)
        
        print("\n📋 Login Credentials:")
        print("\n   Admin:")
        print("   Email: admin@smartlms.com")
        print("   Password: Admin123!")
        
        print("\n   Instructor:")
        print("   Email: instructor@smartlms.com")
        print("   Password: Instructor123!")
        
        print("\n   Student 1:")
        print("   Email: student1@smartlms.com")
        print("   Password: Student123!")
        
        print("\n   Student 2:")
        print("   Email: student2@smartlms.com")
        print("   Password: Student123!")
        
        print("\n🚀 You can now start the server and login with these credentials!")
        print("   Run: python run.py")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()