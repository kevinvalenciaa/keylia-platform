"""
Billing service for Stripe subscription management.

This module handles all Stripe-related operations including:
- Customer management
- Subscription lifecycle
- Webhook event processing
- Usage tracking and limits
"""

import hmac
import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID

import stripe
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.config import settings
from app.models.billing import Subscription, UsageRecord
from app.models.user import Organization

logger = structlog.get_logger()

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


# Plan configuration
class PlanConfig(BaseModel):
    """Configuration for a subscription plan."""

    name: str
    stripe_price_id: str
    video_renders_limit: int | None  # None = unlimited
    ai_generations_limit: int | None
    storage_limit_gb: int | None
    team_members_limit: int | None


PLANS: dict[str, PlanConfig] = {
    "free": PlanConfig(
        name="Free",
        stripe_price_id="",
        video_renders_limit=3,
        ai_generations_limit=10,
        storage_limit_gb=1,
        team_members_limit=1,
    ),
    "starter": PlanConfig(
        name="Starter",
        stripe_price_id=settings.STRIPE_PRICE_STARTER,
        video_renders_limit=20,
        ai_generations_limit=100,
        storage_limit_gb=10,
        team_members_limit=3,
    ),
    "professional": PlanConfig(
        name="Professional",
        stripe_price_id=settings.STRIPE_PRICE_PROFESSIONAL,
        video_renders_limit=100,
        ai_generations_limit=500,
        storage_limit_gb=50,
        team_members_limit=10,
    ),
    "team": PlanConfig(
        name="Team",
        stripe_price_id=settings.STRIPE_PRICE_TEAM,
        video_renders_limit=None,  # Unlimited
        ai_generations_limit=None,
        storage_limit_gb=200,
        team_members_limit=None,
    ),
}


class StripeWebhookError(Exception):
    """Raised when webhook verification or processing fails."""

    pass


class BillingService:
    """Service for managing billing and subscriptions."""

    def __init__(self):
        if not settings.STRIPE_SECRET_KEY:
            logger.warning("Stripe secret key not configured - billing disabled")

    @property
    def is_enabled(self) -> bool:
        """Check if Stripe is configured and enabled."""
        return bool(settings.STRIPE_SECRET_KEY)

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> stripe.Event:
        """
        Verify Stripe webhook signature and return the event.

        Args:
            payload: Raw request body bytes
            signature: Stripe-Signature header value

        Returns:
            Verified Stripe event

        Raises:
            StripeWebhookError: If verification fails
        """
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise StripeWebhookError("Webhook secret not configured")

        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
            return event
        except stripe.SignatureVerificationError as e:
            logger.error("Webhook signature verification failed", error=str(e))
            raise StripeWebhookError(f"Invalid signature: {e}")
        except ValueError as e:
            logger.error("Invalid webhook payload", error=str(e))
            raise StripeWebhookError(f"Invalid payload: {e}")

    async def get_or_create_customer(
        self,
        organization: Organization,
        email: str,
        db: AsyncSession,
    ) -> str:
        """
        Get or create a Stripe customer for an organization.

        Args:
            organization: The organization
            email: Email for the customer
            db: Database session

        Returns:
            Stripe customer ID
        """
        if organization.stripe_customer_id:
            return organization.stripe_customer_id

        # Create new Stripe customer
        customer = stripe.Customer.create(
            email=email,
            name=organization.name,
            metadata={
                "organization_id": str(organization.id),
                "organization_name": organization.name,
            },
        )

        # Save customer ID to organization
        organization.stripe_customer_id = customer.id
        await db.commit()

        logger.info(
            "Created Stripe customer",
            customer_id=customer.id,
            organization_id=str(organization.id),
        )

        return customer.id

    async def create_checkout_session(
        self,
        organization: Organization,
        plan_id: str,
        email: str,
        success_url: str,
        cancel_url: str,
        db: AsyncSession,
        trial_days: int = 7,
    ) -> str:
        """
        Create a Stripe Checkout session for subscription.

        Args:
            organization: The organization subscribing
            plan_id: Plan identifier (starter, professional, team)
            email: Customer email
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            db: Database session
            trial_days: Number of trial days (0 to skip trial)

        Returns:
            Checkout session URL
        """
        if plan_id not in PLANS:
            raise ValueError(f"Invalid plan: {plan_id}")

        plan = PLANS[plan_id]
        if not plan.stripe_price_id:
            raise ValueError(f"Plan {plan_id} has no Stripe price configured")

        customer_id = await self.get_or_create_customer(organization, email, db)

        session_params: dict = {
            "customer": customer_id,
            "mode": "subscription",
            "payment_method_types": ["card"],
            "line_items": [
                {
                    "price": plan.stripe_price_id,
                    "quantity": 1,
                }
            ],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "subscription_data": {
                "metadata": {
                    "organization_id": str(organization.id),
                    "plan_id": plan_id,
                },
            },
            "allow_promotion_codes": True,
        }

        if trial_days > 0:
            session_params["subscription_data"]["trial_period_days"] = trial_days

        session = stripe.checkout.Session.create(**session_params)

        logger.info(
            "Created checkout session",
            session_id=session.id,
            organization_id=str(organization.id),
            plan_id=plan_id,
        )

        return session.url

    async def create_portal_session(
        self,
        organization: Organization,
        return_url: str,
    ) -> str:
        """
        Create a Stripe Customer Portal session.

        Args:
            organization: The organization
            return_url: URL to return to after portal

        Returns:
            Portal session URL
        """
        if not organization.stripe_customer_id:
            raise ValueError("Organization has no Stripe customer")

        session = stripe.billing_portal.Session.create(
            customer=organization.stripe_customer_id,
            return_url=return_url,
        )

        return session.url

    async def handle_checkout_completed(
        self,
        event: stripe.Event,
        db: AsyncSession,
    ) -> None:
        """
        Handle checkout.session.completed webhook event.

        Creates or updates the subscription record.
        """
        session = event.data.object
        subscription_id = session.subscription
        customer_id = session.customer
        metadata = session.get("metadata", {})

        organization_id = metadata.get("organization_id")
        if not organization_id:
            # Try to get from subscription metadata
            sub = stripe.Subscription.retrieve(subscription_id)
            organization_id = sub.metadata.get("organization_id")

        if not organization_id:
            logger.error("No organization_id in checkout session", session_id=session.id)
            return

        plan_id = metadata.get("plan_id", "starter")
        plan = PLANS.get(plan_id, PLANS["starter"])

        # Get subscription details from Stripe
        stripe_sub = stripe.Subscription.retrieve(subscription_id)

        # Create or update subscription record
        result = await db.execute(
            select(Subscription).where(
                Subscription.organization_id == UUID(organization_id)
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            # Update existing subscription
            subscription.stripe_subscription_id = subscription_id
            subscription.stripe_price_id = stripe_sub.items.data[0].price.id
            subscription.plan_name = plan_id
            subscription.status = stripe_sub.status
            subscription.current_period_start = datetime.fromtimestamp(
                stripe_sub.current_period_start, tz=timezone.utc
            )
            subscription.current_period_end = datetime.fromtimestamp(
                stripe_sub.current_period_end, tz=timezone.utc
            )
            subscription.video_renders_limit = plan.video_renders_limit
            subscription.video_renders_used = 0  # Reset on new subscription
        else:
            # Create new subscription
            subscription = Subscription(
                organization_id=UUID(organization_id),
                stripe_subscription_id=subscription_id,
                stripe_price_id=stripe_sub.items.data[0].price.id,
                plan_name=plan_id,
                status=stripe_sub.status,
                current_period_start=datetime.fromtimestamp(
                    stripe_sub.current_period_start, tz=timezone.utc
                ),
                current_period_end=datetime.fromtimestamp(
                    stripe_sub.current_period_end, tz=timezone.utc
                ),
                video_renders_limit=plan.video_renders_limit,
                video_renders_used=0,
            )
            db.add(subscription)

        if stripe_sub.trial_end:
            subscription.trial_end = datetime.fromtimestamp(
                stripe_sub.trial_end, tz=timezone.utc
            )

        await db.commit()

        logger.info(
            "Subscription created/updated from checkout",
            organization_id=organization_id,
            subscription_id=subscription_id,
            plan_id=plan_id,
        )

    async def handle_subscription_updated(
        self,
        event: stripe.Event,
        db: AsyncSession,
    ) -> None:
        """
        Handle customer.subscription.updated webhook event.

        Updates subscription status and period dates.
        """
        stripe_sub = event.data.object
        subscription_id = stripe_sub.id

        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(
                "Subscription not found for update",
                stripe_subscription_id=subscription_id,
            )
            return

        # Update subscription fields
        subscription.status = stripe_sub.status
        subscription.current_period_start = datetime.fromtimestamp(
            stripe_sub.current_period_start, tz=timezone.utc
        )
        subscription.current_period_end = datetime.fromtimestamp(
            stripe_sub.current_period_end, tz=timezone.utc
        )

        if stripe_sub.cancel_at_period_end:
            subscription.status = "cancelled"

        await db.commit()

        logger.info(
            "Subscription updated",
            subscription_id=subscription_id,
            status=subscription.status,
        )

    async def handle_subscription_deleted(
        self,
        event: stripe.Event,
        db: AsyncSession,
    ) -> None:
        """
        Handle customer.subscription.deleted webhook event.

        Marks subscription as cancelled.
        """
        stripe_sub = event.data.object
        subscription_id = stripe_sub.id

        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(
                "Subscription not found for deletion",
                stripe_subscription_id=subscription_id,
            )
            return

        subscription.status = "cancelled"
        await db.commit()

        logger.info(
            "Subscription cancelled",
            subscription_id=subscription_id,
            organization_id=str(subscription.organization_id),
        )

    async def handle_invoice_paid(
        self,
        event: stripe.Event,
        db: AsyncSession,
    ) -> None:
        """
        Handle invoice.paid webhook event.

        Resets usage counters for the new billing period.
        """
        invoice = event.data.object
        subscription_id = invoice.subscription

        if not subscription_id:
            return

        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            return

        # Reset usage counters for new period
        subscription.video_renders_used = 0
        subscription.storage_used_bytes = 0

        await db.commit()

        logger.info(
            "Invoice paid - usage reset",
            subscription_id=subscription_id,
            organization_id=str(subscription.organization_id),
        )

    async def handle_invoice_payment_failed(
        self,
        event: stripe.Event,
        db: AsyncSession,
    ) -> None:
        """
        Handle invoice.payment_failed webhook event.

        Updates subscription status to past_due.
        """
        invoice = event.data.object
        subscription_id = invoice.subscription

        if not subscription_id:
            return

        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            return

        subscription.status = "past_due"
        await db.commit()

        logger.warning(
            "Invoice payment failed",
            subscription_id=subscription_id,
            organization_id=str(subscription.organization_id),
        )

    async def process_webhook_event(
        self,
        event: stripe.Event,
        db: AsyncSession,
    ) -> None:
        """
        Process a verified Stripe webhook event.

        Routes the event to the appropriate handler.
        """
        event_type = event.type

        handlers = {
            "checkout.session.completed": self.handle_checkout_completed,
            "customer.subscription.updated": self.handle_subscription_updated,
            "customer.subscription.deleted": self.handle_subscription_deleted,
            "invoice.paid": self.handle_invoice_paid,
            "invoice.payment_failed": self.handle_invoice_payment_failed,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(event, db)
        else:
            # Log unhandled events at info level to ensure visibility
            # This helps catch new critical events from Stripe (disputes, refunds, etc.)
            logger.info(
                "Received unhandled Stripe webhook event - consider implementing handler",
                event_type=event_type,
                event_id=event.id,
            )

    async def record_usage(
        self,
        organization_id: UUID,
        usage_type: str,
        quantity: int,
        db: AsyncSession,
        project_id: UUID | None = None,
        render_job_id: UUID | None = None,
    ) -> None:
        """
        Record usage and update subscription counters.

        Args:
            organization_id: Organization ID
            usage_type: Type of usage (video_render, ai_script, etc.)
            quantity: Amount of usage
            db: Database session
            project_id: Optional related project
            render_job_id: Optional related render job
        """
        # Create usage record
        record = UsageRecord(
            organization_id=organization_id,
            usage_type=usage_type,
            quantity=quantity,
            project_id=project_id,
            render_job_id=render_job_id,
        )
        db.add(record)

        # Update subscription counters
        if usage_type == "video_render":
            await db.execute(
                update(Subscription)
                .where(Subscription.organization_id == organization_id)
                .values(video_renders_used=Subscription.video_renders_used + quantity)
            )

        await db.commit()

        logger.info(
            "Usage recorded",
            organization_id=str(organization_id),
            usage_type=usage_type,
            quantity=quantity,
        )

    async def get_subscription(
        self,
        organization_id: UUID,
        db: AsyncSession,
    ) -> Subscription | None:
        """Get subscription for an organization."""
        result = await db.execute(
            select(Subscription).where(Subscription.organization_id == organization_id)
        )
        return result.scalar_one_or_none()

    async def check_can_use(
        self,
        organization_id: UUID,
        usage_type: str,
        db: AsyncSession,
    ) -> tuple[bool, str | None]:
        """
        Check if organization can use a feature.

        Returns:
            Tuple of (can_use, reason_if_not)
        """
        subscription = await self.get_subscription(organization_id, db)

        if not subscription:
            return True, None  # No subscription = free tier/trial

        if subscription.status not in ("active", "trialing"):
            return False, "subscription_inactive"

        if usage_type == "video_render":
            if subscription.video_renders_limit is None:
                return True, None  # Unlimited
            if subscription.video_renders_used >= subscription.video_renders_limit:
                return False, "limit_reached"

        return True, None


# Singleton instance
billing_service = BillingService()
