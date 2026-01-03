"""Billing and subscription models."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import Organization
    from app.models.project import Project
    from app.models.render import RenderJob


class Subscription(Base):
    """Subscription model."""

    __tablename__ = "subscriptions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, unique=True
    )
    
    # Stripe
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Plan Details
    plan_name: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Limits
    video_renders_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    video_renders_used: Mapped[int] = mapped_column(Integer, default=0)
    storage_limit_gb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    storage_used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="active")
    
    # Period
    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="subscription"
    )


class UsageRecord(Base):
    """Usage tracking model."""

    __tablename__ = "usage_records"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    
    # Usage Type
    usage_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Amount
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    
    # Reference
    project_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )
    render_job_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("render_jobs.id"), nullable=True
    )
    
    # Timestamps
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    project: Mapped[Optional["Project"]] = relationship("Project")
    render_job: Mapped[Optional["RenderJob"]] = relationship("RenderJob")

