from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


# ============ Exam Pricing Schemas ============

class ExamPricingCreate(BaseModel):
    assessment_id: str
    price_inr: Decimal
    discount_percentage: Decimal = Decimal("0.00")
    is_free: bool = False
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class ExamPricingUpdate(BaseModel):
    price_inr: Optional[Decimal] = None
    discount_percentage: Optional[Decimal] = None
    is_free: Optional[bool] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class ExamPricingResponse(BaseModel):
    id: str
    assessment_id: str
    price_inr: Decimal
    discount_percentage: Decimal
    is_free: bool
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    final_price_inr: Optional[Decimal] = None

    class Config:
        from_attributes = True


# ============ Payment Order Schemas ============

class PaymentOrderCreate(BaseModel):
    assessment_id: str
    # Currency is always INR - no selection needed


class PaymentOrderResponse(BaseModel):
    id: str
    order_id: str
    user_id: str
    assessment_id: str
    amount: Decimal
    currency: str  # Always "INR"
    payment_method: Optional[str] = None
    status: str
    payment_gateway_response: Optional[Dict[str, Any]] = None
    dodopay_payment_id: Optional[str] = None
    dodopay_reference: Optional[str] = None
    failure_reason: Optional[str] = None
    payment_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    checkout_url: Optional[str] = None
    payment_id: Optional[str] = None
    public_key: Optional[str] = None

    class Config:
        from_attributes = True


class PaymentVerification(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentWebhook(BaseModel):
    event: str
    data: Dict[str, Any]


# ============ Exam Access Schemas ============

class ExamAccessCheck(BaseModel):
    has_access: bool
    is_free: bool
    requires_payment: bool
    pricing: Optional[Dict[str, Any]] = None
    payment_order: Optional[Dict[str, Any]] = None
    currency: str = "INR"  # Always INR


# ============ Refund Schemas ============

class RefundRequest(BaseModel):
    payment_order_id: str
    reason: str = "Customer requested refund"


# ============ Certificate Schemas ============

class CertificateGenerate(BaseModel):
    attempt_id: str


class CertificateResponse(BaseModel):
    id: str
    certificate_number: str
    user_id: str
    assessment_id: str
    course_id: str
    score: Decimal
    percentage: Decimal
    grade: Optional[str] = None
    issued_date: datetime
    certificate_url: Optional[str] = None
    verification_code: str
    qr_code_url: Optional[str] = None
    is_verified: bool
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    user_name: Optional[str] = None
    assessment_title: Optional[str] = None
    course_title: Optional[str] = None

    class Config:
        from_attributes = True


class CertificateVerify(BaseModel):
    verification_code: str


class CertificateVerificationResponse(BaseModel):
    valid: bool
    certificate: Optional[CertificateResponse] = None
    message: str


# ============ Badge Schemas ============

class BadgeResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    badge_type: str
    icon_url: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserBadgeResponse(BaseModel):
    id: str
    user_id: str
    badge_id: str
    assessment_id: Optional[str] = None
    certificate_id: Optional[str] = None
    earned_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    badge: BadgeResponse

    class Config:
        from_attributes = True


class UserAchievements(BaseModel):
    total_badges: int
    badges: List[UserBadgeResponse]
    badges_by_type: Dict[str, int]
    bronze_badges: int
    silver_badges: int
    gold_badges: int
    platinum_badges: int

