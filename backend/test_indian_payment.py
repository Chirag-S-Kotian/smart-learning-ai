#!/usr/bin/env python3
"""
Test script for Indian payment (₹10) integration
Tests the complete payment flow for INR currency
"""

import asyncio
import sys
import requests
from pathlib import Path

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
    
    login_data = {
        "email": "student1@smartlms.com",
        "password": "Student123!"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json=login_data,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"   ❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
        
        data = response.json()
        token = data.get("access_token")
        user = data.get("user")
        
        print(f"   ✅ Logged in as: {user.get('email')} ({user.get('id')})")
        return token
        
    except Exception as e:
        print(f"   ❌ Login error: {str(e)}")
        return None


def test_get_pricing(assessment_id, token):
    """Test getting exam pricing"""
    print("\n💰 Testing get exam pricing...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(
            f"{BASE_URL}/payments/pricing/{assessment_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            pricing = response.json()
            print(f"   ✅ Pricing retrieved:")
            print(f"      Price: ₹{pricing.get('price_inr')}")
            print(f"      Discount: {pricing.get('discount_percentage')}%")
            print(f"      Final Price: ₹{pricing.get('final_price_inr', pricing.get('price_inr'))}")
            return pricing
        else:
            print(f"   ❌ Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return None


def test_create_payment_order(assessment_id, token):
    """Test creating a payment order for ₹10"""
    print("\n💳 Testing create payment order (₹10)...")
    
    headers = {"Authorization": f"Bearer {token}"}
    order_data = {
        "assessment_id": assessment_id,
        "currency": "INR"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/payments/orders",
            json=order_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 201:
            order = response.json()
            print(f"   ✅ Payment order created:")
            print(f"      Order ID: {order.get('id')}")
            print(f"      Amount: ₹{order.get('amount')}")
            print(f"      Currency: {order.get('currency')}")
            print(f"      Status: {order.get('status')}")
            if order.get('checkout_url'):
                print(f"      Checkout URL: {order.get('checkout_url')}")
            if order.get('payment_id'):
                print(f"      Payment ID: {order.get('payment_id')}")
            return order
        else:
            print(f"   ❌ Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return None


def test_check_access(assessment_id, token):
    """Test checking exam access"""
    print("\n🔍 Testing exam access check...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(
            f"{BASE_URL}/payments/access/{assessment_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            access = response.json()
            print(f"   ✅ Access check:")
            print(f"      Has Access: {access.get('has_access')}")
            print(f"      Is Free: {access.get('is_free')}")
            if access.get('pricing'):
                print(f"      Price: ₹{access['pricing'].get('price_inr')}")
            return access
        else:
            print(f"   ❌ Failed: {response.status_code}")
            print(f"   Response: {response.text}")
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
    
    # Login
    token = login_test_user()
    if not token:
        print("\n❌ Cannot proceed without authentication")
        return
    
    # Test pricing
    pricing = test_get_pricing(assessment_id, token)
    if not pricing:
        print("\n⚠️  Warning: Could not get pricing")
    
    # Test access check
    access = test_check_access(assessment_id, token)
    
    # Test creating payment order
    order = test_create_payment_order(assessment_id, token)
    
    print("\n" + "="*60)
    if order:
        print("✅ Payment order created successfully!")
        print(f"\n📋 Next steps:")
        print(f"   1. Use the checkout_url to complete payment")
        print(f"   2. Or use DodoPay test credentials to simulate payment")
        print(f"   3. Payment ID: {order.get('payment_id')}")
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

