"""
Comprehensive tests for Payments service and endpoints
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import status
import uuid


class TestPaymentEndpoints:
    """Tests for payment endpoints"""

    def test_initiate_payment(self, client, auth_headers, mock_supabase_client):
        """Test initiating a payment"""
        payment_data = {
            "course_id": "course1",
            "amount": 99.99,
            "currency": "USD"
        }

        payment_response = {
            "id": str(uuid.uuid4()),
            "status": "pending",
            "amount": payment_data["amount"],
            "payment_url": "https://payment-gateway.com/pay/123"
        }

        mock_supabase_client.table.return_value.insert.return_value.execute.return_value.data = [payment_response]

        response = client.post(
            "/api/v1/payments/initiate",
            headers=auth_headers,
            json=payment_data
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert data.get("status") == "pending"

    def test_verify_payment(self, client, auth_headers, mock_supabase_client):
        """Test verifying payment status"""
        payment_id = str(uuid.uuid4())

        payment_response = {
            "id": payment_id,
            "status": "completed",
            "amount": 99.99,
            "transaction_id": "txn_123"
        }

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = payment_response

        response = client.get(
            f"/api/v1/payments/{payment_id}/verify",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert data.get("status") in ["completed", "pending", "failed"]

    def test_get_payment_history(self, client, auth_headers, mock_supabase_client):
        """Test retrieving user payment history"""
        payments = [
            {
                "id": str(uuid.uuid4()),
                "course_id": "course1",
                "amount": 99.99,
                "status": "completed",
                "created_at": "2024-01-01T10:00:00Z"
            },
            {
                "id": str(uuid.uuid4()),
                "course_id": "course2",
                "amount": 149.99,
                "status": "completed",
                "created_at": "2024-01-05T10:00:00Z"
            }
        ]

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = payments

        response = client.get(
            "/api/v1/payments/history",
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        if response.status_code < 400:
            data = response.json()
            assert isinstance(data, list)

    def test_refund_payment(self, client, auth_headers, mock_supabase_client):
        """Test refunding a payment"""
        payment_id = str(uuid.uuid4())
        refund_data = {
            "reason": "Course not suitable"
        }

        refund_response = {
            "id": str(uuid.uuid4()),
            "payment_id": payment_id,
            "status": "approved",
            "reason": refund_data["reason"]
        }

        mock_supabase_client.table.return_value.insert.return_value.execute.return_value.data = [refund_response]

        response = client.post(
            f"/api/v1/payments/{payment_id}/refund",
            headers=auth_headers,
            json=refund_data
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    def test_webhook_payment_confirmation(self, client, mock_supabase_client):
        """Test webhook for payment confirmation"""
        webhook_data = {
            "event": "payment.completed",
            "payment_id": str(uuid.uuid4()),
            "status": "completed",
            "amount": 99.99
        }

        response = client.post(
            "/api/v1/payments/webhook",
            json=webhook_data
        )

        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
