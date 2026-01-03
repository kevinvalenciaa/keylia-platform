"""Property listing endpoints."""

from datetime import date, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.api.v1.projects import get_user_organization_id
from app.database import get_db
from app.models.media import MediaAsset
from app.models.property import PropertyListing
from app.models.user import User

router = APIRouter()


# Schemas
class PropertyCreate(BaseModel):
    address_line1: str = Field(..., min_length=1, max_length=255)
    address_line2: str | None = None
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=50)
    zip_code: str | None = None
    neighborhood: str | None = None
    listing_price: Decimal | None = None
    bedrooms: int | None = Field(None, ge=0, le=50)
    bathrooms: Decimal | None = Field(None, ge=0, le=50)
    square_feet: int | None = Field(None, ge=0)
    lot_size: str | None = None
    year_built: int | None = Field(None, ge=1800, le=2100)
    property_type: str | None = None
    listing_status: str = "for_sale"
    features: list[str] | None = None
    open_house_date: date | None = None
    open_house_start: time | None = None
    open_house_end: time | None = None
    mls_number: str | None = None
    target_audience: str | None = None
    positioning_notes: str | None = None


class PropertyUpdate(BaseModel):
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    neighborhood: str | None = None
    listing_price: Decimal | None = None
    bedrooms: int | None = None
    bathrooms: Decimal | None = None
    square_feet: int | None = None
    lot_size: str | None = None
    year_built: int | None = None
    property_type: str | None = None
    listing_status: str | None = None
    features: list[str] | None = None
    open_house_date: date | None = None
    open_house_start: time | None = None
    open_house_end: time | None = None
    mls_number: str | None = None
    target_audience: str | None = None
    positioning_notes: str | None = None


class MediaAssetResponse(BaseModel):
    id: UUID
    filename: str
    file_type: str
    storage_url: str
    thumbnail_url: str | None
    category: str | None
    width: int | None
    height: int | None
    ai_description: str | None
    ai_tags: list[str] | None

    class Config:
        from_attributes = True


class PropertyResponse(BaseModel):
    id: UUID
    address_line1: str
    address_line2: str | None
    city: str
    state: str
    zip_code: str | None
    neighborhood: str | None
    listing_price: Decimal | None
    bedrooms: int | None
    bathrooms: Decimal | None
    square_feet: int | None
    lot_size: str | None
    year_built: int | None
    property_type: str | None
    listing_status: str
    features: list[str] | None
    open_house_date: date | None
    open_house_start: time | None
    open_house_end: time | None
    mls_number: str | None
    target_audience: str | None
    positioning_notes: str | None
    full_address: str
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


class PropertyWithPhotosResponse(PropertyResponse):
    photos: list[MediaAssetResponse] = []


class PropertyListResponse(BaseModel):
    properties: list[PropertyResponse]
    total: int
    page: int
    limit: int


# Endpoints
@router.get("", response_model=PropertyListResponse)
async def list_properties(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = None,
) -> PropertyListResponse:
    """List all properties for the current user's organization."""
    org_id = await get_user_organization_id(current_user, db)

    # Build query
    query = select(PropertyListing).where(PropertyListing.organization_id == org_id)

    if status_filter:
        query = query.where(PropertyListing.listing_status == status_filter)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            PropertyListing.address_line1.ilike(search_pattern) |
            PropertyListing.city.ilike(search_pattern) |
            PropertyListing.neighborhood.ilike(search_pattern)
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get paginated results
    query = query.order_by(PropertyListing.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    properties = result.scalars().all()

    return PropertyListResponse(
        properties=[PropertyResponse.model_validate(p) for p in properties],
        total=total,
        page=page,
        limit=limit,
    )


@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_data: PropertyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Create a new property listing."""
    org_id = await get_user_organization_id(current_user, db)

    property_listing = PropertyListing(
        organization_id=org_id,
        **property_data.model_dump(),
    )

    db.add(property_listing)
    await db.commit()
    await db.refresh(property_listing)

    return PropertyResponse.model_validate(property_listing)


@router.get("/{property_id}", response_model=PropertyWithPhotosResponse)
async def get_property(
    property_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyWithPhotosResponse:
    """Get a property by ID with its photos."""
    org_id = await get_user_organization_id(current_user, db)

    result = await db.execute(
        select(PropertyListing).where(
            PropertyListing.id == property_id,
            PropertyListing.organization_id == org_id,
        )
    )
    property_listing = result.scalar_one_or_none()

    if not property_listing:
        raise HTTPException(status_code=404, detail="Property not found")

    # Get associated photos
    photos_result = await db.execute(
        select(MediaAsset).where(
            MediaAsset.organization_id == org_id,
            MediaAsset.file_type == "image",
            MediaAsset.storage_key.contains(str(property_id))
        ).order_by(MediaAsset.created_at)
    )
    photos = photos_result.scalars().all()

    response = PropertyWithPhotosResponse.model_validate(property_listing)
    response.photos = [MediaAssetResponse.model_validate(p) for p in photos]

    return response


@router.patch("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: UUID,
    property_data: PropertyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Update a property listing."""
    org_id = await get_user_organization_id(current_user, db)

    result = await db.execute(
        select(PropertyListing).where(
            PropertyListing.id == property_id,
            PropertyListing.organization_id == org_id,
        )
    )
    property_listing = result.scalar_one_or_none()

    if not property_listing:
        raise HTTPException(status_code=404, detail="Property not found")

    update_data = property_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(property_listing, field, value)

    await db.commit()
    await db.refresh(property_listing)

    return PropertyResponse.model_validate(property_listing)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a property listing."""
    org_id = await get_user_organization_id(current_user, db)

    result = await db.execute(
        select(PropertyListing).where(
            PropertyListing.id == property_id,
            PropertyListing.organization_id == org_id,
        )
    )
    property_listing = result.scalar_one_or_none()

    if not property_listing:
        raise HTTPException(status_code=404, detail="Property not found")

    await db.delete(property_listing)
    await db.commit()


@router.get("/{property_id}/photos", response_model=list[MediaAssetResponse])
async def get_property_photos(
    property_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MediaAssetResponse]:
    """Get all photos for a property."""
    org_id = await get_user_organization_id(current_user, db)

    # Verify property access
    result = await db.execute(
        select(PropertyListing).where(
            PropertyListing.id == property_id,
            PropertyListing.organization_id == org_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Property not found")

    # Get photos - look for media assets associated with this property
    photos_result = await db.execute(
        select(MediaAsset).where(
            MediaAsset.organization_id == org_id,
            MediaAsset.file_type == "image",
            MediaAsset.storage_key.contains(str(property_id))
        ).order_by(MediaAsset.created_at)
    )
    photos = photos_result.scalars().all()

    return [MediaAssetResponse.model_validate(p) for p in photos]
