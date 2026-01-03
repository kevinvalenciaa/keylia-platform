"""Brand kit model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import Organization


class BrandKit(Base):
    """Brand kit model for agent branding."""

    __tablename__ = "brand_kits"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Agent Info
    agent_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    agent_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    brokerage_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    agent_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    agent_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Visual Identity
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_light_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    primary_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    secondary_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    accent_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    
    # Typography
    heading_font: Mapped[str] = mapped_column(String(100), default="Inter")
    body_font: Mapped[str] = mapped_column(String(100), default="Inter")
    
    # Headshot for videos
    headshot_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="brand_kits"
    )

