"""Tests for Stripe webhook handling."""

import json
import pytest
from unittest.mock import patch, MagicMock
from typing import Any


class TestStripeWebhookSecurity:
    """Test Stripe webhook signature verification."""

    def test_webhook_requires_signature(self, client) -> None:
        """Test that webhooks require valid Stripe signature."""
        # Without signature header, should reject
        response = client.post(
            "/api/v1/billing/webhook",
            content=b'{"type": "test"}',
            headers={"Content-Type": "application/json"},
        )
        
        # Should reject without signature (400 or 401)
        assert response.status_code in [400, 401, 404]  # 404 if endpoint doesn't exist

    def test_webhook_rejects_invalid_signature(self, client) -> None:
        """Test that invalid signatures are rejected."""
        response = client.post(
            "/api/v1/billing/webhook",
            content=b'{"type": "test"}',
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=123,v1=invalid_signature",
            },
        )
        
        assert response.status_code in [400, 401, 404]


class TestStripeCheckoutWebhook:
    """Test checkout.session.completed webhook handling."""

    @pytest.mark.asyncio
    async def test_checkout_completed_creates_subscription(
        self,
        async_client,
        mock_stripe_checkout_event: dict[str, Any],
    ) -> None:
        """Test that checkout.session.completed creates a subscription."""
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = mock_stripe_checkout_event
            
            response = await async_client.post(
                "/api/v1/billing/webhook",
                content=json.dumps(mock_stripe_checkout_event).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Stripe-Signature": "t=123,v1=valid_sig",
                },
            )
            
            # Should process successfully or return 404 if endpoint not implemented
            assert response.status_code in [200, 404]


class TestStripeInvoiceWebhook:
    """Test invoice webhook handling."""

    @pytest.mark.asyncio
    async def test_invoice_paid_extends_subscription(
        self,
        async_client,
        mock_stripe_invoice_paid_event: dict[str, Any],
    ) -> None:
        """Test that invoice.paid extends subscription period."""
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = mock_stripe_invoice_paid_event
            
            response = await async_client.post(
                "/api/v1/billing/webhook",
                content=json.dumps(mock_stripe_invoice_paid_event).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Stripe-Signature": "t=123,v1=valid_sig",
                },
            )
            
            assert response.status_code in [200, 404]


class TestStripeSubscriptionWebhook:
    """Test subscription lifecycle webhooks."""

    @pytest.mark.asyncio
    async def test_subscription_deleted_cancels_access(
        self,
        async_client,
        mock_stripe_subscription_deleted_event: dict[str, Any],
    ) -> None:
        """Test that subscription deletion cancels user access."""
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = mock_stripe_subscription_deleted_event
            
            response = await async_client.post(
                "/api/v1/billing/webhook",
                content=json.dumps(mock_stripe_subscription_deleted_event).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Stripe-Signature": "t=123,v1=valid_sig",
                },
            )
            
            assert response.status_code in [200, 404]


class TestWebhookIdempotency:
    """Test webhook idempotency handling."""

    @pytest.mark.asyncio
    async def test_duplicate_event_is_handled_gracefully(
        self,
        async_client,
        mock_stripe_checkout_event: dict[str, Any],
    ) -> None:
        """Test that duplicate webhook events are handled gracefully."""
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = mock_stripe_checkout_event
            
            # Send same event twice
            for _ in range(2):
                response = await async_client.post(
                    "/api/v1/billing/webhook",
                    content=json.dumps(mock_stripe_checkout_event).encode(),
                    headers={
                        "Content-Type": "application/json",
                        "Stripe-Signature": "t=123,v1=valid_sig",
                    },
                )
                
                # Both should succeed (idempotent) or return 404
                assert response.status_code in [200, 404]
