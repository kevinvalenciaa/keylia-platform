"""
Billing API endpoints.

Handles subscription management, checkout, and Stripe webhooks
with proper signature verification for production security.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_organization_context, OrganizationContext
from app.api.v1.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.services.billing import (
    billing_service,
    PLANS,
    StripeWebhookError,
)

router = APIRouter()


# Request/Response Schemas
class PlanResponse(BaseModel):
    """Plan details response."""

    id: str
    name: str
    video_renders_limit: int | None
    ai_generations_limit: int | None
    storage_limit_gb: int | None
    team_members_limit: int | None


class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""

    plan_id: Literal["starter", "professional", "team"] = Field(
        ..., description="Plan to subscribe to"
    )
    trial_days: int = Field(default=7, ge=0, le=30, description="Trial period days")


class CheckoutResponse(BaseModel):
    """Checkout session response."""

    url: str
    session_id: str | None = None


class PortalResponse(BaseModel):
    """Customer portal session response."""

    url: str


class SubscriptionResponse(BaseModel):
    """Current subscription details."""

    plan_name: str
    status: str
    video_renders_used: int
    video_renders_limit: int | None
    storage_used_bytes: int
    storage_limit_gb: int | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    trial_end: datetime | None
    can_generate: bool
    is_trial: bool


class UsageResponse(BaseModel):
    """Usage information response."""

    video_renders_used: int
    video_renders_limit: int | None
    video_renders_remaining: int | None
    storage_used_bytes: int
    storage_limit_bytes: int | None
    can_generate: bool
    reason: str | None = None


class CanGenerateResponse(BaseModel):
    """Check if generation is allowed."""

    can_generate: bool
    reason: str | None = None
    remaining: int | None = None


# Endpoints
@router.get("/plans", response_model=list[PlanResponse])
async def list_plans() -> list[PlanResponse]:
    """
    List available subscription plans.

    Returns all plans with their limits and features.
    """
    return [
        PlanResponse(
            id=plan_id,
            name=plan.name,
            video_renders_limit=plan.video_renders_limit,
            ai_generations_limit=plan.ai_generations_limit,
            storage_limit_gb=plan.storage_limit_gb,
            team_members_limit=plan.team_members_limit,
        )
        for plan_id, plan in PLANS.items()
        if plan_id != "free"  # Don't show free plan in list
    ]


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """
    Create a Stripe Checkout session for subscription.

    Requires owner access to the organization.
    """
    if not billing_service.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured. Contact support.",
        )

    context = await get_organization_context(current_user, db)

    if not context.can_manage_billing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can manage billing",
        )

    success_url = f"{settings.FRONTEND_URL}/dashboard?checkout=success"
    cancel_url = f"{settings.FRONTEND_URL}/pricing?checkout=cancelled"

    try:
        url = await billing_service.create_checkout_session(
            organization=context.organization,
            plan_id=request.plan_id,
            email=current_user.email,
            success_url=success_url,
            cancel_url=cancel_url,
            db=db,
            trial_days=request.trial_days,
        )
        return CheckoutResponse(url=url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalResponse:
    """
    Create a Stripe Customer Portal session.

    Allows customers to manage their subscription, payment methods, and invoices.
    """
    if not billing_service.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured. Contact support.",
        )

    context = await get_organization_context(current_user, db)

    if not context.can_manage_billing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can manage billing",
        )

    if not context.organization.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription. Please subscribe first.",
        )

    return_url = f"{settings.FRONTEND_URL}/settings"

    try:
        url = await billing_service.create_portal_session(
            organization=context.organization,
            return_url=return_url,
        )
        return PortalResponse(url=url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """
    Get current subscription details.

    Returns subscription status, usage, and limits.
    """
    context = await get_organization_context(current_user, db, include_subscription=True)

    sub = context.subscription

    if not sub:
        # Return free tier defaults
        return SubscriptionResponse(
            plan_name="free",
            status="active",
            video_renders_used=0,
            video_renders_limit=3,
            storage_used_bytes=0,
            storage_limit_gb=1,
            current_period_start=None,
            current_period_end=None,
            trial_end=None,
            can_generate=True,
            is_trial=False,
        )

    can_generate = True
    if sub.video_renders_limit is not None:
        can_generate = sub.video_renders_used < sub.video_renders_limit

    if sub.status not in ("active", "trialing"):
        can_generate = False

    return SubscriptionResponse(
        plan_name=sub.plan_name,
        status=sub.status,
        video_renders_used=sub.video_renders_used,
        video_renders_limit=sub.video_renders_limit,
        storage_used_bytes=sub.storage_used_bytes,
        storage_limit_gb=sub.storage_limit_gb,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        trial_end=sub.trial_end,
        can_generate=can_generate,
        is_trial=sub.status == "trialing",
    )


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsageResponse:
    """
    Get current usage statistics.

    Returns usage counts and remaining allowances.
    """
    context = await get_organization_context(current_user, db, include_subscription=True)

    sub = context.subscription

    if not sub:
        return UsageResponse(
            video_renders_used=0,
            video_renders_limit=3,
            video_renders_remaining=3,
            storage_used_bytes=0,
            storage_limit_bytes=1 * 1024 * 1024 * 1024,  # 1GB
            can_generate=True,
        )

    video_renders_remaining = None
    if sub.video_renders_limit is not None:
        video_renders_remaining = max(0, sub.video_renders_limit - sub.video_renders_used)

    storage_limit_bytes = None
    if sub.storage_limit_gb is not None:
        storage_limit_bytes = sub.storage_limit_gb * 1024 * 1024 * 1024

    can_generate, reason = await billing_service.check_can_use(
        context.organization_id, "video_render", db
    )

    return UsageResponse(
        video_renders_used=sub.video_renders_used,
        video_renders_limit=sub.video_renders_limit,
        video_renders_remaining=video_renders_remaining,
        storage_used_bytes=sub.storage_used_bytes,
        storage_limit_bytes=storage_limit_bytes,
        can_generate=can_generate,
        reason=reason,
    )


@router.get("/can-generate", response_model=CanGenerateResponse)
async def check_can_generate(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CanGenerateResponse:
    """
    Check if the user can generate content.

    Quick check for UI to show upgrade prompts.
    """
    # If billing is disabled, always allow
    if not billing_service.is_enabled:
        return CanGenerateResponse(can_generate=True)

    context = await get_organization_context(current_user, db, include_subscription=True)

    can_generate, reason = await billing_service.check_can_use(
        context.organization_id, "video_render", db
    )

    remaining = None
    if context.subscription and context.subscription.video_renders_limit is not None:
        remaining = max(
            0, context.subscription.video_renders_limit - context.subscription.video_renders_used
        )

    return CanGenerateResponse(
        can_generate=can_generate,
        reason=reason,
        remaining=remaining,
    )


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Handle Stripe webhook events.

    This endpoint verifies the webhook signature before processing
    any events to prevent spoofed requests.
    """
    if not billing_service.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured",
        )

    # Get raw body for signature verification
    payload = await request.body()

    try:
        # Verify signature and parse event
        event = billing_service.verify_webhook_signature(
            payload=payload,
            signature=stripe_signature,
        )

        # Process the event
        await billing_service.process_webhook_event(event, db)

        return {"status": "success", "event_type": event.type}

    except StripeWebhookError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
