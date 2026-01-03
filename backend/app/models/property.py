"""Property listing model."""

from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, Time, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import Organization


class PropertyListing(Base):
    """Property listing model."""

    __tablename__ = "property_listings"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    
    # Address
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    neighborhood: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Details
    listing_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    bedrooms: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    bathrooms: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 1), nullable=True)
    square_feet: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lot_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    property_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Status
    listing_status: Mapped[str] = mapped_column(String(50), default="for_sale", index=True)
    
    # Features (array)
    features: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    
    # Open House
    open_house_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    open_house_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    open_house_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    
    # MLS
    mls_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Positioning
    target_audience: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    positioning_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    
    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.append(f"{self.city}, {self.state}")
        if self.zip_code:
            parts[-1] += f" {self.zip_code}"
        return ", ".join(parts)

