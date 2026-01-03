"""Project and Scene models."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import Organization, User
    from app.models.brand_kit import BrandKit
    from app.models.property import PropertyListing
    from app.models.media import MediaAsset
    from app.models.render import RenderJob


class ProjectType(str, Enum):
    """Project type enumeration."""
    
    LISTING_TOUR = "listing_tour"
    PROMO_VIDEO = "promo_video"
    INFOGRAPHIC = "infographic"


class ProjectStatus(str, Enum):
    """Project status enumeration."""
    
    DRAFT = "draft"
    SCRIPT_PENDING = "script_pending"
    SCRIPT_READY = "script_ready"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(Base):
    """Project model."""

    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    created_by_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    
    # References
    property_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("property_listings.id"), nullable=True
    )
    brand_kit_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("brand_kits.id"), nullable=True
    )
    
    # Basic Info
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default=ProjectStatus.DRAFT.value, index=True)
    
    # Style Settings (JSON)
    style_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    voice_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    infographic_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Generated Content
    generated_script: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    generated_caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_hashtags: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="projects")
    created_by: Mapped["User"] = relationship("User")
    property_listing: Mapped[Optional["PropertyListing"]] = relationship("PropertyListing")
    brand_kit: Mapped[Optional["BrandKit"]] = relationship("BrandKit")
    scenes: Mapped[List["Scene"]] = relationship(
        "Scene", back_populates="project", order_by="Scene.sequence_order"
    )
    media_assets: Mapped[List["MediaAsset"]] = relationship(
        "MediaAsset", back_populates="project"
    )
    render_jobs: Mapped[List["RenderJob"]] = relationship(
        "RenderJob", back_populates="project"
    )


class Scene(Base):
    """Scene model for video projects."""

    __tablename__ = "scenes"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    
    # Order & Timing
    sequence_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Content
    narration_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    on_screen_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Visual
    media_asset_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("media_assets.id"), nullable=True
    )
    
    # Camera Movement (JSON)
    camera_movement: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Transition
    transition_type: Mapped[str] = mapped_column(String(50), default="crossfade")
    transition_duration_ms: Mapped[int] = mapped_column(Integer, default=500)
    
    # Overlay Settings (JSON)
    overlay_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="scenes")
    media_asset: Mapped[Optional["MediaAsset"]] = relationship("MediaAsset")

