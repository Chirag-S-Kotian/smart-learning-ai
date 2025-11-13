import requests
import hmac
import hashlib
import json
from typing import Optional, Dict, Any
from datetime import datetime
from app.config import settings
from app.core.supabase_client import supabase_client


class DodoPayService:
    """
    DodoPay Payment Gateway Integration
    Supports: Indian Currency (INR), UPI, Credit/Debit Cards, Netbanking, and Wallets
    """
    
    def __init__(self):
        self.public_key = settings.DODOPAY_PUBLIC_KEY
        self.secret_key = settings.DODOPAY_SECRET_KEY
        self.api_url = settings.DODOPAY_API_URL
        self.webhook_secret = settings.DODOPAY_WEBHOOK_SECRET
        self.currency = "INR"  # Only Indian Rupees
        self.supported_payment_methods = ["upi", "card", "netbanking", "wallet", "bank_transfer"]
        
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers with authentication"""
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
            "X-Public-Key": self.public_key
        }
    
    def create_payment(
        self,
        user_id: str,
        assessment_id: str,
        amount: float,
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a payment request with DodoPay in Indian Rupees (INR)
        
        Args:
            user_id: User ID making the payment
            assessment_id: Assessment ID being purchased
            amount: Payment amount in INR
            customer_email: Customer email
            customer_name: Customer name
            
        Returns:
            Payment response with payment_id and checkout_url
        """
        try:
            # Create unique reference
            reference = f"EXAM_{assessment_id}_{user_id}_{int(datetime.utcnow().timestamp())}"
            
            # Prepare payment payload - Amount in paise (smallest unit for INR)
            # Convert INR to paise (1 INR = 100 paise)
            amount_in_paise = int(amount * 100)
            
            payload = {
                "amount": amount_in_paise,
                "currency": self.currency,
                "reference": reference,
                "description": f"Exam Access Fee - Assessment {assessment_id}",
                "customer": {
                    "email": customer_email or f"user_{user_id}@smartlms.com",
                    "name": customer_name or f"User {user_id}"
                },
                "metadata": {
                    "user_id": user_id,
                    "assessment_id": assessment_id,
                    "type": "exam_access",
                    "country": "IN"
                },
                "callback_url": f"{settings.FRONTEND_URL}/payment/callback",
                "webhook_url": f"{settings.API_V1_PREFIX}/payments/webhook",
                "payment_methods": self.supported_payment_methods,
                "redirect_url": f"{settings.FRONTEND_URL}/payment/success"
            }
            
            # Make API request
            response = requests.post(
                f"{self.api_url}/payments",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            payment_data = response.json()
            
            # Save payment order to database
            order_data = {
                "order_id": payment_data.get("payment_id") or payment_data.get("id"),
                "user_id": user_id,
                "assessment_id": assessment_id,
                "amount": amount,
                "currency": self.currency,
                "status": "pending",
                "payment_gateway_response": payment_data,
                "dodopay_payment_id": payment_data.get("payment_id") or payment_data.get("id"),
                "dodopay_reference": reference
            }
            
            result = supabase_client.table("payment_orders").insert(order_data).execute()
            
            return {
                "success": True,
                "payment_id": payment_data.get("payment_id") or payment_data.get("id"),
                "checkout_url": payment_data.get("checkout_url") or payment_data.get("payment_url"),
                "reference": reference,
                "order": result.data[0],
                "public_key": self.public_key,
                "currency": self.currency,
                "amount": amount
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"DodoPay API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Payment creation failed: {str(e)}")
    
    def verify_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Verify payment status with DodoPay
        
        Args:
            payment_id: DodoPay payment ID
            
        Returns:
            Payment status and details
        """
        try:
            response = requests.get(
                f"{self.api_url}/payments/{payment_id}",
                headers=self._get_headers(),
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Payment verification failed: {str(e)}")
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook signature from DodoPay
        
        Args:
            payload: Webhook payload as string
            signature: Signature from X-Signature header
            
        Returns:
            True if signature is valid
        """
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
        except Exception:
            return False
    
    def complete_payment(
        self,
        payment_id: str,
        payment_reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete payment after verification
        
        Args:
            payment_id: DodoPay payment ID
            payment_reference: Payment reference
            
        Returns:
            Completed payment details
        """
        try:
            # Verify payment status
            payment_status = self.verify_payment(payment_id)
            
            if payment_status.get("status") != "completed" and payment_status.get("status") != "success":
                raise Exception(f"Payment not completed. Status: {payment_status.get('status')}")
            
            # Get payment order from database
            if payment_reference:
                order_result = supabase_client.table("payment_orders").select("*").eq(
                    "dodopay_reference", payment_reference
                ).single().execute()
            else:
                order_result = supabase_client.table("payment_orders").select("*").eq(
                    "dodopay_payment_id", payment_id
                ).single().execute()
            
            order = order_result.data
            
            if not order:
                raise Exception("Payment order not found")
            
            # Update order status
            update_data = {
                "status": "completed",
                "payment_method": payment_status.get("payment_method", "card"),
                "payment_date": datetime.utcnow().isoformat(),
                "payment_gateway_response": payment_status
            }
            
            updated_order = supabase_client.table("payment_orders").update(update_data).eq(
                "id", order["id"]
            ).execute()
            
            # Grant exam access
            access_data = {
                "user_id": order["user_id"],
                "assessment_id": order["assessment_id"],
                "payment_order_id": order["id"],
                "is_free": False
            }
            
            supabase_client.table("exam_access").insert(access_data).execute()
            
            # Log transaction
            transaction_data = {
                "payment_order_id": order["id"],
                "transaction_type": "payment",
                "gateway_response": payment_status,
                "status": "completed",
                "amount": order["amount"]
            }
            
            supabase_client.table("payment_transactions").insert(transaction_data).execute()
            
            return {
                "success": True,
                "order": updated_order.data[0],
                "message": "Payment completed successfully"
            }
            
        except Exception as e:
            # Mark payment as failed
            if payment_reference:
                supabase_client.table("payment_orders").update({
                    "status": "failed",
                    "failure_reason": str(e)
                }).eq("dodopay_reference", payment_reference).execute()
            
            raise Exception(f"Payment completion failed: {str(e)}")
    
    def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """
        Handle DodoPay webhook events
        
        Args:
            event_type: Webhook event type
            payload: Webhook payload
            
        Returns:
            True if handled successfully
        """
        try:
            payment_id = payload.get("payment_id") or payload.get("id")
            
            if event_type == "payment.completed" or event_type == "payment.success":
                # Complete the payment
                self.complete_payment(payment_id)
                
            elif event_type == "payment.failed":
                # Mark as failed
                order = supabase_client.table("payment_orders").select("*").eq(
                    "dodopay_payment_id", payment_id
                ).single().execute()
                
                if order.data:
                    supabase_client.table("payment_orders").update({
                        "status": "failed",
                        "failure_reason": payload.get("failure_reason", "Payment failed"),
                        "payment_gateway_response": payload
                    }).eq("id", order.data["id"]).execute()
            
            elif event_type == "payment.refunded":
                # Mark as refunded
                order = supabase_client.table("payment_orders").select("*").eq(
                    "dodopay_payment_id", payment_id
                ).single().execute()
                
                if order.data:
                    supabase_client.table("payment_orders").update({
                        "status": "refunded",
                        "payment_gateway_response": payload
                    }).eq("id", order.data["id"]).execute()
                    
                    # Revoke access
                    supabase_client.table("exam_access").delete().eq(
                        "payment_order_id", order.data["id"]
                    ).execute()
            
            return True
            
        except Exception as e:
            print(f"Webhook handling error: {str(e)}")
            return False
    
    def create_refund(
        self,
        payment_id: str,
        amount: Optional[float] = None,
        reason: str = "Customer requested refund"
    ) -> Dict[str, Any]:
        """
        Create a refund for a payment
        
        Args:
            payment_id: DodoPay payment ID
            amount: Refund amount (None for full refund)
            reason: Refund reason
            
        Returns:
            Refund details
        """
        try:
            payload = {
                "payment_id": payment_id,
                "reason": reason
            }
            
            if amount:
                payload["amount"] = amount
            
            response = requests.post(
                f"{self.api_url}/refunds",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            refund_data = response.json()
            
            # Update order status
            order = supabase_client.table("payment_orders").select("*").eq(
                "dodopay_payment_id", payment_id
            ).single().execute()
            
            if order.data:
                supabase_client.table("payment_orders").update({
                    "status": "refunded",
                    "payment_gateway_response": refund_data
                }).eq("id", order.data["id"]).execute()
                
                # Revoke access
                supabase_client.table("exam_access").delete().eq(
                    "payment_order_id", order.data["id"]
                ).execute()
                
                # Log transaction
                supabase_client.table("payment_transactions").insert({
                    "payment_order_id": order.data["id"],
                    "transaction_type": "refund",
                    "gateway_response": refund_data,
                    "status": "completed",
                    "amount": amount or order.data["amount"]
                }).execute()
            
            return {
                "success": True,
                "refund": refund_data,
                "message": "Refund processed successfully"
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Refund failed: {str(e)}")
    
    def get_payment_methods(self) -> Dict[str, Any]:
        """
        Get available Indian payment methods
        
        Returns:
            Available payment methods for INR
        """
        return {
            "currency": self.currency,
            "methods": self.supported_payment_methods,
            "description": "Indian Payment Methods",
            "payment_method_details": {
                "upi": {
                    "name": "Unified Payments Interface",
                    "description": "Direct bank transfer via UPI",
                    "availability": "24/7"
                },
                "card": {
                    "name": "Credit/Debit Cards",
                    "description": "Visa, Mastercard, American Express",
                    "availability": "24/7"
                },
                "netbanking": {
                    "name": "Netbanking",
                    "description": "Direct bank transfer via netbanking",
                    "availability": "24/7"
                },
                "wallet": {
                    "name": "Digital Wallets",
                    "description": "Paytm, PhonePe, Google Pay, Amazon Pay",
                    "availability": "24/7"
                },
                "bank_transfer": {
                    "name": "Bank Transfer",
                    "description": "Direct bank account transfer",
                    "availability": "Business hours"
                }
            }
        }


# Singleton instance
dodopay_service = DodoPayService()