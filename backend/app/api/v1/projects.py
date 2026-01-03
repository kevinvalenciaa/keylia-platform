"""Project endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.project import Project, ProjectStatus, ProjectType, Scene
from app.models.render import RenderJob
from app.models.user import OrganizationMember, User

router = APIRouter()


# Schemas
class StyleSettings(BaseModel):
    tone: str = "modern"
    pace: str = "moderate"
    music_vibe: str = "cinematic"
    duration_seconds: int = 30
    platform: str = "instagram_reels"
    aspect_ratio: str = "9:16"


class VoiceSettings(BaseModel):
    enabled: bool = True
    language: str = "en-US"
    gender: str = "female"
    style: str = "friendly"
    voice_id: str | None = None


class InfographicSettings(BaseModel):
    layout: str = "single_card"
    emphasis: str = "feature_driven"
    animation: str = "light_motion"


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern="^(listing_tour|promo_video|infographic)$")
    property_id: UUID | None = None
    brand_kit_id: UUID | None = None
    style_settings: StyleSettings | None = None
    voice_settings: VoiceSettings | None = None
    infographic_settings: InfographicSettings | None = None


class ProjectUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    style_settings: StyleSettings | None = None
    voice_settings: VoiceSettings | None = None
    infographic_settings: InfographicSettings | None = None
    generated_script: dict[str, Any] | None = None
    generated_caption: str | None = None
    generated_hashtags: list[str] | None = None


class SceneCreate(BaseModel):
    sequence_order: int
    start_time_ms: int
    duration_ms: int
    narration_text: str | None = None
    on_screen_text: str | None = None
    media_asset_id: UUID | None = None
    camera_movement: dict[str, Any] = {}
    transition_type: str = "crossfade"
    transition_duration_ms: int = 500
    overlay_settings: dict[str, Any] = {}


class SceneUpdate(BaseModel):
    narration_text: str | None = None
    on_screen_text: str | None = None
    media_asset_id: UUID | None = None
    camera_movement: dict[str, Any] | None = None
    transition_type: str | None = None
    overlay_settings: dict[str, Any] | None = None


class SceneResponse(BaseModel):
    id: UUID
    project_id: UUID
    sequence_order: int
    start_time_ms: int
    duration_ms: int
    narration_text: str | None
    on_screen_text: str | None
    media_asset_id: UUID | None
    camera_movement: dict[str, Any]
    transition_type: str
    transition_duration_ms: int
    overlay_settings: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    id: UUID
    title: str
    type: str
    status: str
    property_id: UUID | None
    brand_kit_id: UUID | None
    style_settings: dict[str, Any]
    voice_settings: dict[str, Any]
    infographic_settings: dict[str, Any]
    generated_script: dict[str, Any] | None
    generated_caption: str | None
    generated_hashtags: list[str] | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int
    page: int
    limit: int


# Helper to get user's organization
async def get_user_organization_id(user: User, db: AsyncSession) -> UUID:
    """Get the user's primary organization ID."""
    result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == user.id)
        .order_by(OrganizationMember.joined_at)
        .limit(1)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=400, detail="User has no organization")
    return member.organization_id


# Endpoints
@router.get("", response_model=ProjectListResponse)
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: str | None = None,
    status: str | None = None,
    property_id: UUID | None = None,
) -> ProjectListResponse:
    """List all projects for the current user's organization."""
    org_id = await get_user_organization_id(current_user, db)
    
    # Build query
    query = select(Project).where(Project.organization_id == org_id)
    
    if type:
        query = query.where(Project.type == type)
    if status:
        query = query.where(Project.status == status)
    if property_id:
        query = query.where(Project.property_id == property_id)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    
    # Get paginated results
    query = query.order_by(Project.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        limit=limit,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create a new project."""
    org_id = await get_user_organization_id(current_user, db)
    
    project = Project(
        organization_id=org_id,
        created_by_id=current_user.id,
        title=project_data.title,
        type=project_data.type,
        property_id=project_data.property_id,
        brand_kit_id=project_data.brand_kit_id,
        style_settings=project_data.style_settings.model_dump() if project_data.style_settings else {},
        voice_settings=project_data.voice_settings.model_dump() if project_data.voice_settings else {},
        infographic_settings=project_data.infographic_settings.model_dump() if project_data.infographic_settings else {},
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Get a project by ID."""
    org_id = await get_user_organization_id(current_user, db)
    
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id, Project.organization_id == org_id)
        .options(selectinload(Project.scenes))
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Update a project."""
    org_id = await get_user_organization_id(current_user, db)
    
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == org_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update fields
    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            if field in ["style_settings", "voice_settings", "infographic_settings"] and isinstance(value, BaseModel):
                value = value.model_dump()
            setattr(project, field, value)
    
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a project and its related render jobs."""
    org_id = await get_user_organization_id(current_user, db)

    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == org_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete related render jobs first (foreign key constraint)
    render_jobs_result = await db.execute(
        select(RenderJob).where(RenderJob.project_id == project_id)
    )
    render_jobs = render_jobs_result.scalars().all()
    for render_job in render_jobs:
        await db.delete(render_job)

    await db.delete(project)
    await db.commit()


# Scene endpoints
@router.get("/{project_id}/scenes", response_model=list[SceneResponse])
async def list_scenes(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SceneResponse]:
    """List all scenes for a project."""
    org_id = await get_user_organization_id(current_user, db)
    
    # Verify project access
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == org_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
    
    result = await db.execute(
        select(Scene)
        .where(Scene.project_id == project_id)
        .order_by(Scene.sequence_order)
    )
    scenes = result.scalars().all()
    
    return [SceneResponse.model_validate(s) for s in scenes]


@router.post("/{project_id}/scenes", response_model=SceneResponse, status_code=status.HTTP_201_CREATED)
async def create_scene(
    project_id: UUID,
    scene_data: SceneCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SceneResponse:
    """Create a new scene."""
    org_id = await get_user_organization_id(current_user, db)
    
    # Verify project access
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == org_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
    
    scene = Scene(
        project_id=project_id,
        **scene_data.model_dump(),
    )
    
    db.add(scene)
    await db.commit()
    await db.refresh(scene)
    
    return SceneResponse.model_validate(scene)


@router.patch("/{project_id}/scenes/{scene_id}", response_model=SceneResponse)
async def update_scene(
    project_id: UUID,
    scene_id: UUID,
    scene_data: SceneUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SceneResponse:
    """Update a scene."""
    org_id = await get_user_organization_id(current_user, db)
    
    # Verify project access
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == org_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
    
    result = await db.execute(
        select(Scene).where(Scene.id == scene_id, Scene.project_id == project_id)
    )
    scene = result.scalar_one_or_none()
    
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    
    # Update fields
    update_data = scene_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(scene, field, value)
    
    await db.commit()
    await db.refresh(scene)
    
    return SceneResponse.model_validate(scene)

