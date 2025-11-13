from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import List
from app.schemas.payment import (
    ExamPricingCreate, ExamPricingUpdate, ExamPricingResponse,
    PaymentOrderCreate, PaymentOrderResponse, PaymentVerification,
    PaymentWebhook, ExamAccessCheck, RefundRequest,
    CertificateGenerate, CertificateResponse, CertificateVerify,
    CertificateVerificationResponse, BadgeResponse, UserBadgeResponse,
    UserAchievements
)
from app.dependencies import (
    get_current_user, get_current_instructor,
    get_current_admin
)
from app.core.supabase_client import supabase_client
from app.services.dodopay_service import dodopay_service
from app.services.certificate_service import certificate_service
from app.config import settings

router = APIRouter()


# ============ Exam Pricing Endpoints ============

@router.post("/pricing", response_model=ExamPricingResponse, status_code=status.HTTP_201_CREATED)
async def create_exam_pricing(
    pricing_data: ExamPricingCreate,
    current_user: dict = Depends(get_current_instructor)
):
    """Create pricing for an exam in INR (Instructor/Admin only)"""
    try:
        # Verify assessment ownership
        assessment = supabase_client.table("assessments").select(
            "id, courses(instructor_id)"
        ).eq("id", pricing_data.assessment_id).single().execute()
        
        if not assessment.data:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        if current_user["role"] != "admin":
            if assessment.data["courses"]["instructor_id"] != current_user["id"]:
                raise HTTPException(status_code=403, detail="Not authorized")
        
        # Calculate final price with discount
        discount_multiplier = 1 - (pricing_data.discount_percentage / 100)
        
        pricing_dict = pricing_data.model_dump()
        result = supabase_client.table("exam_pricing").insert(pricing_dict).execute()
        
        pricing = result.data[0]
        pricing["final_price_inr"] = pricing["price_inr"] * discount_multiplier
        
        return pricing
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create pricing: {str(e)}")


@router.get("/pricing/{assessment_id}", response_model=ExamPricingResponse)
async def get_exam_pricing(assessment_id: str):
    """Get pricing for an exam in INR"""
    try:
        result = supabase_client.table("exam_pricing").select("*").eq(
            "assessment_id", assessment_id
        ).single().execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Pricing not found")
        
        pricing = result.data
        discount_multiplier = 1 - (pricing["discount_percentage"] / 100)
        pricing["final_price_inr"] = pricing["price_inr"] * discount_multiplier
        
        return pricing
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/pricing/{assessment_id}", response_model=ExamPricingResponse)
async def update_exam_pricing(
    assessment_id: str,
    pricing_data: ExamPricingUpdate,
    current_user: dict = Depends(get_current_instructor)
):
    """Update exam pricing"""
    try:
        update_dict = pricing_data.model_dump(exclude_unset=True)
        
        result = supabase_client.table("exam_pricing").update(update_dict).eq(
            "assessment_id", assessment_id
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Pricing not found")
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Payment Order Endpoints ============

@router.post("/orders", response_model=PaymentOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_order(
    order_data: PaymentOrderCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a payment order for exam access (INR only)"""
    try:
        # Check if already has access
        existing_access = supabase_client.table("exam_access").select("id").eq(
            "user_id", current_user["id"]
        ).eq("assessment_id", order_data.assessment_id).execute()
        
        if existing_access.data:
            raise HTTPException(status_code=400, detail="Already have access to this exam")
        
        # Get pricing
        pricing = supabase_client.table("exam_pricing").select("*").eq(
            "assessment_id", order_data.assessment_id
        ).single().execute()
        
        if not pricing.data:
            raise HTTPException(status_code=404, detail="Exam pricing not configured")
        
        price_data = pricing.data
        
        if price_data["is_free"]:
            # Grant free access
            access_data = {
                "user_id": current_user["id"],
                "assessment_id": order_data.assessment_id,
                "is_free": True
            }
            supabase_client.table("exam_access").insert(access_data).execute()
            
            raise HTTPException(status_code=400, detail="This exam is free")
        
        # Calculate amount - INR only
        discount_multiplier = 1 - (price_data["discount_percentage"] / 100)
        amount = price_data["price_inr"] * discount_multiplier
        
        # Create payment order with INR
        order_result = dodopay_service.create_payment(
            user_id=current_user["id"],
            assessment_id=order_data.assessment_id,
            amount=amount,
            customer_email=current_user.get("email"),
            customer_name=current_user.get("full_name")
        )
        
        order_response = order_result["order"]
        # Add payment gateway details
        if "checkout_url" not in order_response:
            order_response["checkout_url"] = order_result.get("checkout_url")
        if "payment_id" not in order_response:
            order_response["payment_id"] = order_result.get("payment_id")
        if "public_key" not in order_response:
            order_response["public_key"] = order_result.get("public_key")
        if "currency" not in order_response:
            order_response["currency"] = "INR"
        
        return order_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")


@router.post("/verify")
async def verify_payment(
    verification_data: PaymentVerification,
    current_user: dict = Depends(get_current_user)
):
    """Verify payment after completion"""
    try:
        result = dodopay_service.complete_payment(
            payment_id=verification_data.razorpay_payment_id,
            payment_reference=verification_data.razorpay_order_id
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def payment_webhook(request: Request):
    """Handle payment gateway webhooks"""
    try:
        payload = await request.json()
        
        # Verify webhook signature (implement based on your gateway)
        # For Razorpay, verify X-Razorpay-Signature header
        
        event = payload.get("event")
        dodopay_service.handle_webhook(event, payload)
        
        return {"status": "success"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Exam Access Endpoints ============

@router.get("/access/{assessment_id}", response_model=ExamAccessCheck)
async def check_exam_access(
    assessment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Check if user has access to an exam (INR pricing)"""
    try:
        # Check if exam is free
        pricing = supabase_client.table("exam_pricing").select("*").eq(
            "assessment_id", assessment_id
        ).execute()
        
        is_free = False
        pricing_info = None
        
        if pricing.data:
            price_data = pricing.data[0]
            is_free = price_data["is_free"]
            
            discount_multiplier = 1 - (price_data["discount_percentage"] / 100)
            # Only show INR pricing
            pricing_info = {
                **price_data,
                "currency": "INR",
                "final_price_inr": price_data["price_inr"] * discount_multiplier
            }
        
        # Check if user has access
        access = supabase_client.table("exam_access").select("*").eq(
            "user_id", current_user["id"]
        ).eq("assessment_id", assessment_id).execute()
        
        has_access = bool(access.data) or is_free
        
        # Get pending payment order if exists
        pending_order = None
        if not has_access:
            order = supabase_client.table("payment_orders").select("*").eq(
                "user_id", current_user["id"]
            ).eq("assessment_id", assessment_id).eq("status", "pending").execute()
            
            if order.data:
                pending_order = order.data[0]
        
        return {
            "has_access": has_access,
            "is_free": is_free,
            "requires_payment": not has_access and not is_free,
            "pricing": pricing_info,
            "payment_order": pending_order,
            "currency": "INR"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-purchases")
async def get_my_purchases(current_user: dict = Depends(get_current_user)):
    """Get user's purchase history"""
    try:
        result = supabase_client.table("payment_orders").select(
            "*, assessments(title, courses(title))"
        ).eq("user_id", current_user["id"]).eq(
            "status", "completed"
        ).order("payment_date", desc=True).execute()
        
        return {"purchases": result.data}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Certificate Endpoints ============

@router.post("/certificates/generate", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
async def generate_certificate(
    cert_data: CertificateGenerate,
    current_user: dict = Depends(get_current_user)
):
    """Generate certificate after passing exam"""
    try:
        result = await certificate_service.generate_certificate(cert_data.attempt_id)
        
        certificate = result["certificate"]
        
        # Add related data
        user = supabase_client.table("users").select("full_name").eq(
            "id", certificate["user_id"]
        ).single().execute()
        
        assessment = supabase_client.table("assessments").select(
            "title, courses(title)"
        ).eq("id", certificate["assessment_id"]).single().execute()
        
        return {
            **certificate,
            "user_name": user.data["full_name"],
            "assessment_name": assessment.data["title"],
            "course_name": assessment.data["courses"]["title"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/certificates/my", response_model=List[CertificateResponse])
async def get_my_certificates(current_user: dict = Depends(get_current_user)):
    """Get user's certificates"""
    try:
        result = supabase_client.table("certificates").select(
            """
            *,
            users(full_name),
            assessments(title),
            courses(title)
            """
        ).eq("user_id", current_user["id"]).order(
            "issued_date", desc=True
        ).execute()
        
        certificates = []
        for cert in result.data:
            certificates.append({
                **cert,
                "user_name": cert["users"]["full_name"],
                "assessment_name": cert["assessments"]["title"],
                "course_name": cert["courses"]["title"]
            })
        
        return certificates
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/certificates/verify", response_model=CertificateVerificationResponse)
async def verify_certificate(verify_data: CertificateVerify):
    """Verify certificate authenticity (public endpoint)"""
    try:
        result = certificate_service.verify_certificate(verify_data.verification_code)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/certificates/{certificate_id}", response_model=CertificateResponse)
async def get_certificate(certificate_id: str):
    """Get certificate details (public for verification)"""
    try:
        result = supabase_client.table("certificates").select(
            """
            *,
            users(full_name),
            assessments(title),
            courses(title)
            """
        ).eq("id", certificate_id).single().execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Certificate not found")
        
        cert = result.data
        return {
            **cert,
            "user_name": cert["users"]["full_name"],
            "assessment_name": cert["assessments"]["title"],
            "course_name": cert["courses"]["title"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Badge Endpoints ============

@router.get("/badges", response_model=List[BadgeResponse])
async def get_all_badges():
    """Get all available badges"""
    try:
        result = supabase_client.table("badges").select("*").eq(
            "is_active", True
        ).execute()
        
        return result.data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/badges/my", response_model=List[UserBadgeResponse])
async def get_my_badges(current_user: dict = Depends(get_current_user)):
    """Get user's earned badges"""
    try:
        result = supabase_client.table("user_badges").select(
            """
            *,
            badges(*),
            assessments(title)
            """
        ).eq("user_id", current_user["id"]).order(
            "earned_at", desc=True
        ).execute()
        
        badges = []
        for ub in result.data:
            badges.append({
                "id": ub["id"],
                "user_id": ub["user_id"],
                "badge": ub["badges"],
                "assessment_id": ub.get("assessment_id"),
                "assessment_name": ub["assessments"]["title"] if ub.get("assessments") else None,
                "earned_at": ub["earned_at"]
            })
        
        return badges
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/achievements", response_model=UserAchievements)
async def get_achievements(current_user: dict = Depends(get_current_user)):
    """Get user's complete achievement summary"""
    try:
        # Get certificates
        certs = supabase_client.table("certificates").select(
            "*", count="exact"
        ).eq("user_id", current_user["id"]).execute()
        
        # Get badges
        badges_result = supabase_client.table("user_badges").select(
            """
            *,
            badges(*),
            assessments(title)
            """
        ).eq("user_id", current_user["id"]).execute()
        
        # Get recent certificates
        recent_certs = supabase_client.table("certificates").select(
            """
            *,
            users(full_name),
            assessments(title),
            courses(title)
            """
        ).eq("user_id", current_user["id"]).order(
            "issued_date", desc=True
        ).limit(5).execute()
        
        # Format badges
        formatted_badges = []
        for ub in badges_result.data:
            formatted_badges.append({
                "id": ub["id"],
                "user_id": ub["user_id"],
                "badge": ub["badges"],
                "assessment_id": ub.get("assessment_id"),
                "assessment_name": ub["assessments"]["title"] if ub.get("assessments") else None,
                "earned_at": ub["earned_at"]
            })
        
        # Format certificates
        formatted_certs = []
        for cert in recent_certs.data:
            formatted_certs.append({
                **cert,
                "user_name": cert["users"]["full_name"],
                "assessment_name": cert["assessments"]["title"],
                "course_name": cert["courses"]["title"]
            })
        
        # Achievement summary
        badge_types = {}
        for badge in badges_result.data:
            badge_type = badge["badges"]["badge_type"]
            badge_types[badge_type] = badge_types.get(badge_type, 0) + 1
        
        return {
            "total_certificates": certs.count,
            "total_badges": len(badges_result.data),
            "badges": formatted_badges,
            "recent_certificates": formatted_certs,
            "achievements_summary": {
                "certificates_count": certs.count,
                "badges_by_type": badge_types,
                "bronze_badges": badge_types.get("bronze", 0),
                "silver_badges": badge_types.get("silver", 0),
                "gold_badges": badge_types.get("gold", 0),
                "platinum_badges": badge_types.get("platinum", 0)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Admin Endpoints ============

@router.post("/refund", status_code=status.HTTP_200_OK)
async def process_refund(
    refund_data: RefundRequest,
    current_user: dict = Depends(get_current_admin)
):
    """Process refund (Admin only)"""
    try:
        # Get payment order to find payment_id
        order = supabase_client.table("payment_orders").select("dodopay_payment_id").eq(
            "id", refund_data.payment_order_id
        ).single().execute()
        
        if not order.data or not order.data.get("dodopay_payment_id"):
            raise HTTPException(status_code=404, detail="Payment order not found")
        
        result = dodopay_service.create_refund(
            payment_id=order.data["dodopay_payment_id"],
            reason=refund_data.reason
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))