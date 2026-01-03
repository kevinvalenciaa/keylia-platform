"""Brand kit endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.api.v1.projects import get_user_organization_id
from app.database import get_db
from app.models.brand_kit import BrandKit
from app.models.user import User

router = APIRouter()


class BrandKitCreate(BaseModel):
    name: str
    agent_name: str | None = None
    agent_title: str | None = None
    brokerage_name: str | None = None
    agent_email: str | None = None
    agent_phone: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    heading_font: str = "Inter"
    body_font: str = "Inter"


class BrandKitUpdate(BaseModel):
    name: str | None = None
    agent_name: str | None = None
    agent_title: str | None = None
    brokerage_name: str | None = None
    agent_email: str | None = None
    agent_phone: str | None = None
    logo_url: str | None = None
    headshot_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    heading_font: str | None = None
    body_font: str | None = None
    is_default: bool | None = None


class BrandKitResponse(BaseModel):
    id: UUID
    name: str
    is_default: bool
    agent_name: str | None
    agent_title: str | None
    brokerage_name: str | None
    agent_email: str | None
    agent_phone: str | None
    logo_url: str | None
    headshot_url: str | None
    primary_color: str | None
    secondary_color: str | None
    accent_color: str | None
    heading_font: str
    body_font: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[BrandKitResponse])
async def list_brand_kits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BrandKitResponse]:
    """List all brand kits."""
    org_id = await get_user_organization_id(current_user, db)
    
    result = await db.execute(
        select(BrandKit).where(BrandKit.organization_id == org_id)
    )
    brand_kits = result.scalars().all()
    
    return [BrandKitResponse.model_validate(bk) for bk in brand_kits]


@router.post("", response_model=BrandKitResponse, status_code=status.HTTP_201_CREATED)
async def create_brand_kit(
    brand_kit_data: BrandKitCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BrandKitResponse:
    """Create a new brand kit."""
    org_id = await get_user_organization_id(current_user, db)
    
    brand_kit = BrandKit(
        organization_id=org_id,
        **brand_kit_data.model_dump(),
    )
    
    db.add(brand_kit)
    await db.commit()
    await db.refresh(brand_kit)
    
    return BrandKitResponse.model_validate(brand_kit)


@router.get("/{brand_kit_id}", response_model=BrandKitResponse)
async def get_brand_kit(
    brand_kit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BrandKitResponse:
    """Get a brand kit by ID."""
    org_id = await get_user_organization_id(current_user, db)
    
    result = await db.execute(
        select(BrandKit).where(
            BrandKit.id == brand_kit_id,
            BrandKit.organization_id == org_id,
        )
    )
    brand_kit = result.scalar_one_or_none()
    
    if not brand_kit:
        raise HTTPException(status_code=404, detail="Brand kit not found")
    
    return BrandKitResponse.model_validate(brand_kit)


@router.patch("/{brand_kit_id}", response_model=BrandKitResponse)
async def update_brand_kit(
    brand_kit_id: UUID,
    brand_kit_data: BrandKitUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BrandKitResponse:
    """Update a brand kit."""
    org_id = await get_user_organization_id(current_user, db)
    
    result = await db.execute(
        select(BrandKit).where(
            BrandKit.id == brand_kit_id,
            BrandKit.organization_id == org_id,
        )
    )
    brand_kit = result.scalar_one_or_none()
    
    if not brand_kit:
        raise HTTPException(status_code=404, detail="Brand kit not found")
    
    update_data = brand_kit_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(brand_kit, field, value)
    
    await db.commit()
    await db.refresh(brand_kit)
    
    return BrandKitResponse.model_validate(brand_kit)


@router.delete("/{brand_kit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand_kit(
    brand_kit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a brand kit."""
    org_id = await get_user_organization_id(current_user, db)
    
    result = await db.execute(
        select(BrandKit).where(
            BrandKit.id == brand_kit_id,
            BrandKit.organization_id == org_id,
        )
    )
    brand_kit = result.scalar_one_or_none()
    
    if not brand_kit:
        raise HTTPException(status_code=404, detail="Brand kit not found")
    
    await db.delete(brand_kit)
    await db.commit()

