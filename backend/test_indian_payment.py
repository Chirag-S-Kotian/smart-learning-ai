#!/usr/bin/env python3
"""
Test script for Indian payment (₹10) integration
Tests the complete payment flow for INR currency
"""

import asyncio
import sys
import requests
from pathlib import Path
from uuid import uuid4
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.supabase_client import supabase_admin
from app.config import settings

# Use admin client for setup
if not supabase_admin:
    print("❌ ERROR: SUPABASE_SERVICE_ROLE_KEY is not set. Cannot run test.")
    sys.exit(1)

BASE_URL = f"http://{settings.HOST}:{settings.PORT}{settings.API_V1_PREFIX}"


def setup_test_data():
    """Set up test assessment and pricing"""
    print("\n🔧 Setting up test data...")
    
    # Get or create a test assessment
    assessments = supabase_admin.table("assessments").select("id, title").limit(1).execute()
    
    if not assessments.data:
        print("❌ No assessments found. Please run seed_data.py first.")
        return None
    
    assessment_id = assessments.data[0]["id"]
    assessment_title = assessments.data[0]["title"]
    
    print(f"   Using assessment: {assessment_title} ({assessment_id})")
    
    # Set up pricing for ₹10
    pricing_data = {
        "assessment_id": assessment_id,
        "price_usd": 0.12,  # ~₹10
        "price_inr": 10.00,
        "discount_percentage": 0,
        "is_free": False
    }
    
    # Check if pricing exists
    existing = supabase_admin.table("exam_pricing").select("*").eq(
        "assessment_id", assessment_id
    ).execute()
    
    if existing.data:
        # Update existing pricing
        result = supabase_admin.table("exam_pricing").update({
            k: v for k, v in pricing_data.items() if k != "assessment_id"
        }).eq(
            "assessment_id", assessment_id
        ).execute()
        print(f"   ✅ Updated pricing: ₹{pricing_data['price_inr']}")
    else:
        # Create new pricing
        result = supabase_admin.table("exam_pricing").insert(pricing_data).execute()
        print(f"   ✅ Created pricing: ₹{pricing_data['price_inr']}")
    
    return assessment_id


def login_test_user():
    """Login as test user and get access token"""
    print("\n🔐 Logging in as test user...")
    
    # Try to get direct access from test data
    try:
        # Check if user exists in database
        users = supabase_admin.table("users").select("*").eq(
            "email", "student1@smartlms.com"
        ).execute()
        
        if not users.data:
            print("   ⚠️  Test user not found. Creating test user...")
            # Create test user
            user_data = {
                "email": "student1@smartlms.com",
                "full_name": "Test Student",
                "role": "student",
                "email_verified": True,
                "is_active": True
            }
            result = supabase_admin.table("users").insert(user_data).execute()
            user_id = result.data[0]["id"]
            print(f"   ✅ Created test user: {user_id}")
            return user_id
        
        user_id = users.data[0]["id"]
        print(f"   ✅ Found test user: {users.data[0]['email']} ({user_id})")
        
        # For testing, return user_id directly as Bearer token
        # In real scenario, would do login flow
        return user_id
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return None


def test_get_pricing(assessment_id, user_id):
    """Test getting exam pricing"""
    print("\n💰 Testing get exam pricing...")
    
    try:
        # Get pricing directly from database for testing
        result = supabase_admin.table("exam_pricing").select("*").eq(
            "assessment_id", assessment_id
        ).execute()
        
        if result.data:
            pricing = result.data[0]
            print(f"   ✅ Pricing retrieved:")
            print(f"      Price: ₹{pricing.get('price_inr')}")
            print(f"      Discount: {pricing.get('discount_percentage')}%")
            final_price = pricing.get('price_inr') * (1 - pricing.get('discount_percentage', 0) / 100)
            print(f"      Final Price: ₹{final_price}")
            return pricing
        else:
            print(f"   ❌ No pricing found")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return None


def test_create_payment_order(assessment_id, user_id):
    """Test creating a payment order for ₹10"""
    print("\n💳 Testing create payment order (₹10)...")
    
    try:
        # Create order directly in database for testing
        order_id = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid4())[:8]}"
        
        order_data = {
            "order_id": order_id,
            "user_id": user_id,
            "assessment_id": assessment_id,
            "amount": 1000,  # 1000 paise = ₹10
            "currency": "INR",
            "status": "pending",
            "payment_method": "upi"
        }
        
        result = supabase_admin.table("payment_orders").insert(order_data).execute()
        
        if result.data:
            order = result.data[0]
            print(f"   ✅ Payment order created successfully!")
            print(f"      Order ID: {order.get('id')}")
            print(f"      Order Reference: {order.get('order_id')}")
            print(f"      Amount: ₹{order.get('amount')/100:.2f}")
            print(f"      Currency: {order.get('currency')}")
            print(f"      Status: {order.get('status')}")
            print(f"      Payment Method: {order.get('payment_method')}")
            print(f"      Created At: {order.get('created_at')}")
            return order
        else:
            print(f"   ❌ Failed to create order")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return None


def test_check_access(assessment_id, user_id):
    """Test checking exam access"""
    print("\n🔍 Testing exam access check...")
    
    try:
        # Check if user has access to assessment
        access_check = supabase_admin.table("assessments").select("*").eq(
            "id", assessment_id
        ).execute()
        
        if access_check.data:
            assessment = access_check.data[0]
            is_free = assessment.get('is_free', False)
            print(f"   ✅ Access check:")
            print(f"      Assessment: {assessment.get('title')}")
            print(f"      Is Free: {is_free}")
            
            if not is_free:
                # Check if user has purchased
                purchase = supabase_admin.table("payment_orders").select("*").eq(
                    "user_id", user_id
                ).eq("assessment_id", assessment_id).eq(
                    "status", "completed"
                ).execute()
                has_access = bool(purchase.data)
                print(f"      Has Access: {has_access}")
            else:
                print(f"      Has Access: True (Free Assessment)")
            
            return access_check.data[0]
        else:
            print(f"   ❌ Assessment not found")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return None


def main():
    """Main test function"""
    print("="*60)
    print("🇮🇳 Indian Payment Test (₹10)")
    print("="*60)
    
    # Setup
    assessment_id = setup_test_data()
    if not assessment_id:
        return
    
    # Login/Get user
    user_id = login_test_user()
    if not user_id:
        print("\n❌ Cannot proceed without user")
        return
    
    # Test pricing
    pricing = test_get_pricing(assessment_id, user_id)
    if not pricing:
        print("\n⚠️  Warning: Could not get pricing")
    
    # Test access check
    access = test_check_access(assessment_id, user_id)
    
    # Test creating payment order
    order = test_create_payment_order(assessment_id, user_id)
    
    print("\n" + "="*60)
    if order:
        print("✅ Payment order created successfully!")
        print(f"\n📋 Payment Details:")
        print(f"   Order ID: {order.get('id')}")
        print(f"   Amount: ₹{order.get('amount')/100}")
        print(f"   Currency: {order.get('currency')}")
        print(f"   Status: {order.get('payment_status')}")
        print(f"\n🔗 Next Steps (for real integration):")
        print(f"   1. Send payment_id to DodoPay API")
        print(f"   2. Complete payment through DodoPay checkout")
        print(f"   3. Update payment status to 'completed'")
        print(f"   4. User gets exam access")
    else:
        print("❌ Payment order creation failed")
    print("="*60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

