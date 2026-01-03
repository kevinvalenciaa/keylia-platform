"""Render job model."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


class RenderStatus(str, Enum):
    """Render job status enumeration."""
    
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RenderType(str, Enum):
    """Render type enumeration."""
    
    PREVIEW = "preview"
    FINAL = "final"
    EXPORT_VARIANT = "export_variant"


class RenderJob(Base):
    """Render job model."""

    __tablename__ = "render_jobs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    
    # Type
    render_type: Mapped[str] = mapped_column(
        String(50), default=RenderType.FINAL.value
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50), default=RenderStatus.QUEUED.value, index=True
    )
    progress_percent: Mapped[int] = mapped_column(SmallInteger, default=0)
    
    # Render Settings (JSON)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Output
    output_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    subtitle_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Error Tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Worker Info
    worker_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="render_jobs")

