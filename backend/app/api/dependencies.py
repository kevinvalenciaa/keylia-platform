"""Shared API dependencies and utilities.

This module contains common dependencies used across multiple API routes
to ensure DRY principles and consistent behavior.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import Organization, OrganizationMember, User
from app.models.billing import Subscription


class OrganizationContext:
    """Context object containing organization-related data for the current user."""

    def __init__(
        self,
        user: User,
        organization_id: UUID,
        organization: Organization | None = None,
        role: str = "member",
        subscription: Subscription | None = None,
    ):
        self.user = user
        self.organization_id = organization_id
        self.organization = organization
        self.role = role
        self.subscription = subscription

    @property
    def is_owner(self) -> bool:
        return self.role == "owner"

    @property
    def is_admin(self) -> bool:
        return self.role in ("owner", "admin")

    @property
    def can_manage_billing(self) -> bool:
        return self.role == "owner"


async def get_user_organization_id(user: User, db: AsyncSession) -> UUID:
    """
    Get the user's primary organization ID.

    Returns the organization the user joined first (primary organization).

    Args:
        user: The authenticated user
        db: Database session

    Returns:
        UUID of the user's primary organization

    Raises:
        HTTPException: If user has no organization membership
    """
    result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == user.id)
        .order_by(OrganizationMember.joined_at)
        .limit(1)
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no organization. Please complete onboarding.",
        )

    return member.organization_id


async def get_organization_context(
    user: User,
    db: AsyncSession,
    include_subscription: bool = False,
) -> OrganizationContext:
    """
    Get full organization context for the current user.

    Args:
        user: The authenticated user
        db: Database session
        include_subscription: Whether to load subscription data

    Returns:
        OrganizationContext with user's organization details

    Raises:
        HTTPException: If user has no organization membership
    """
    result = await db.execute(
        select(OrganizationMember, Organization)
        .join(Organization, OrganizationMember.organization_id == Organization.id)
        .where(OrganizationMember.user_id == user.id)
        .order_by(OrganizationMember.joined_at)
        .limit(1)
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no organization. Please complete onboarding.",
        )

    member, organization = row

    subscription = None
    if include_subscription:
        sub_result = await db.execute(
            select(Subscription).where(Subscription.organization_id == organization.id)
        )
        subscription = sub_result.scalar_one_or_none()

    return OrganizationContext(
        user=user,
        organization_id=organization.id,
        organization=organization,
        role=member.role,
        subscription=subscription,
    )


async def require_org_admin(
    user: User,
    db: AsyncSession,
) -> OrganizationContext:
    """
    Require the user to be an admin or owner of their organization.

    Args:
        user: The authenticated user
        db: Database session

    Returns:
        OrganizationContext if user is admin/owner

    Raises:
        HTTPException: If user is not an admin or owner
    """
    context = await get_organization_context(user, db)

    if not context.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or owner access required",
        )

    return context


async def require_org_owner(
    user: User,
    db: AsyncSession,
) -> OrganizationContext:
    """
    Require the user to be the owner of their organization.

    Args:
        user: The authenticated user
        db: Database session

    Returns:
        OrganizationContext if user is owner

    Raises:
        HTTPException: If user is not the owner
    """
    context = await get_organization_context(user, db)

    if not context.is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access required",
        )

    return context


async def check_usage_limit(
    context: OrganizationContext,
    usage_type: str,
    db: AsyncSession,
) -> bool:
    """
    Check if the organization has remaining usage for a specific type.

    Args:
        context: Organization context with subscription
        usage_type: Type of usage to check (e.g., 'video_render', 'ai_generation')
        db: Database session

    Returns:
        True if usage is within limits, False otherwise
    """
    if not context.subscription:
        # Reload subscription if not present
        result = await db.execute(
            select(Subscription).where(
                Subscription.organization_id == context.organization_id
            )
        )
        context.subscription = result.scalar_one_or_none()

    if not context.subscription:
        # No subscription means trial or free tier
        return True

    sub = context.subscription

    if sub.status not in ("active", "trialing"):
        return False

    if usage_type == "video_render":
        if sub.video_renders_limit is None:
            return True  # Unlimited
        return sub.video_renders_used < sub.video_renders_limit

    # Add other usage types as needed
    return True


def require_usage_available(usage_type: str):
    """
    Dependency factory to require available usage for a specific type.

    Usage:
        @router.post("/render")
        async def create_render(
            context: OrganizationContext = Depends(require_usage_available("video_render")),
            db: AsyncSession = Depends(get_db),
        ):
            ...
    """

    async def dependency(
        user: User,
        db: AsyncSession,
    ) -> OrganizationContext:
        context = await get_organization_context(user, db, include_subscription=True)

        if not await check_usage_limit(context, usage_type, db):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Usage limit reached for {usage_type}. Please upgrade your plan.",
            )

        return context

    return dependency
