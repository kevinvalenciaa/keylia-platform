"""Tour video generation endpoints."""

import asyncio
import json
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.auth import get_current_user
from app.api.v1.projects import get_user_organization_id
from app.config import settings
from app.database import get_db
from app.models.media import MediaAsset
from app.models.project import Project, Scene
from app.models.property import PropertyListing
from app.models.render import RenderJob, RenderStatus
from app.models.user import User
from app.services.ai.elevenlabs_service import elevenlabs_service

router = APIRouter()


# Schemas
class VoiceSettings(BaseModel):
    voice_id: str | None = None
    language: str = "en-US"
    style: str = "professional"  # professional, friendly, warm
    gender: str = "female"  # male, female


class StyleSettings(BaseModel):
    tone: str = "modern"  # luxury, cozy, modern, minimal, bold
    pace: str = "moderate"  # slow, moderate, fast
    music_style: str | None = None
    video_model: str = "kling"  # kling, kling_pro, kling_v2, veo3, veo3_fast, minimax, runway


class GenerateTourVideoRequest(BaseModel):
    duration_seconds: Literal[15, 30, 60] = 30
    voice_settings: VoiceSettings = Field(default_factory=VoiceSettings)
    style_settings: StyleSettings = Field(default_factory=StyleSettings)
    brand_kit_id: UUID | None = None
    photo_order: list[UUID] | None = None  # Custom order of photos to use


class GenerateTourVideoResponse(BaseModel):
    project_id: UUID
    render_job_id: UUID
    status: str
    message: str


class TourVideoProgressResponse(BaseModel):
    project_id: UUID
    render_job_id: UUID
    status: str
    progress_percent: int
    current_step: str | None
    step_details: dict[str, Any]
    estimated_remaining_seconds: int | None
    output_url: str | None
    error_message: str | None


class ScenePreview(BaseModel):
    sequence_order: int
    image_url: str
    narration_text: str | None
    duration_ms: int
    camera_movement: str


class TourVideoPreviewResponse(BaseModel):
    project_id: UUID
    title: str
    duration_seconds: int
    scenes: list[ScenePreview]
    generated_script: dict[str, Any] | None
    generated_caption: str | None
    generated_hashtags: list[str] | None


class VoiceOption(BaseModel):
    voice_id: str
    name: str
    label: str
    preview_url: str | None
    category: str


# Duration to scene count mapping
DURATION_SCENE_CONFIG = {
    15: {"scene_count": 3, "scene_duration_ms": 5000},
    30: {"scene_count": 5, "scene_duration_ms": 6000},
    60: {"scene_count": 8, "scene_duration_ms": 7500},
}


# Redis client for idempotency
_redis_client = None


async def get_redis_for_idempotency():
    """Get Redis client for idempotency checks."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        import redis.asyncio as redis
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )
        await _redis_client.ping()
        return _redis_client
    except Exception:
        return None


# Endpoints
@router.post("/from-listing/{listing_id}", response_model=GenerateTourVideoResponse)
async def generate_tour_video_from_listing(
    listing_id: UUID,
    request: GenerateTourVideoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
) -> GenerateTourVideoResponse:
    """
    Generate a tour video from an existing listing.

    This creates a new project, generates a script, creates scenes,
    and queues a Celery task for video generation.

    Include X-Idempotency-Key header to prevent duplicate job creation
    on retries or double-clicks.
    """
    # Check idempotency key if provided
    if x_idempotency_key:
        redis = await get_redis_for_idempotency()
        if redis:
            try:
                existing = await redis.get(f"idempotency:{x_idempotency_key}")
                if existing:
                    # Return cached response
                    cached = json.loads(existing)
                    return GenerateTourVideoResponse(**cached)
            except Exception:
                pass  # Continue with request if Redis fails

    org_id = await get_user_organization_id(current_user, db)

    # Get the listing
    result = await db.execute(
        select(PropertyListing).where(
            PropertyListing.id == listing_id,
            PropertyListing.organization_id == org_id,
        )
    )
    listing = result.scalar_one_or_none()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Get photos for this listing
    # TODO: Add property_listing_id FK to MediaAsset for proper relationship
    # Current pattern uses storage_key matching which is fragile
    # The listing_id is validated as UUID by FastAPI path parameter
    listing_id_str = str(listing_id)
    photos_result = await db.execute(
        select(MediaAsset).where(
            MediaAsset.organization_id == org_id,
            MediaAsset.file_type == "image",
            MediaAsset.processing_status == "completed",
            # Use literal_column to ensure the pattern is safely escaped
            # Match pattern: listings/{listing_id}/ in storage key
            MediaAsset.storage_key.like(f"%listings/{listing_id_str}/%"),
        ).order_by(MediaAsset.created_at)
    )
    photos = list(photos_result.scalars().all())

    if not photos:
        raise HTTPException(
            status_code=400,
            detail="No photos found for this listing. Please upload photos first.",
        )

    # Apply custom photo order if provided
    if request.photo_order:
        photo_map = {p.id: p for p in photos}
        ordered_photos = []
        for photo_id in request.photo_order:
            if photo_id in photo_map:
                ordered_photos.append(photo_map[photo_id])
        photos = ordered_photos if ordered_photos else photos

    # Get scene configuration for duration
    config = DURATION_SCENE_CONFIG[request.duration_seconds]
    scene_count = min(config["scene_count"], len(photos))
    scene_duration_ms = config["scene_duration_ms"]

    # Create the project
    project = Project(
        organization_id=org_id,
        created_by_id=current_user.id,
        property_id=listing_id,
        brand_kit_id=request.brand_kit_id,
        title=f"Tour Video - {listing.full_address}",
        type="listing_tour",
        status="script_pending",
        style_settings={
            "tone": request.style_settings.tone,
            "pace": request.style_settings.pace,
            "music_vibe": request.style_settings.music_style or "cinematic",
            "duration_seconds": request.duration_seconds,
            "platform": "instagram_reels",
            "aspect_ratio": "9:16",
            "video_model": request.style_settings.video_model,
        },
        voice_settings={
            "enabled": True,
            "language": request.voice_settings.language,
            "gender": request.voice_settings.gender,
            "style": request.voice_settings.style,
            "voice_id": request.voice_settings.voice_id,
        },
    )

    db.add(project)
    await db.flush()

    # Create scenes
    camera_movements = ["zoom_in", "pan_right", "zoom_out", "pan_left", "orbit_right"]
    scenes = []

    for i, photo in enumerate(photos[:scene_count]):
        scene = Scene(
            project_id=project.id,
            sequence_order=i,
            start_time_ms=i * scene_duration_ms,
            duration_ms=scene_duration_ms,
            media_asset_id=photo.id,
            camera_movement={
                "type": camera_movements[i % len(camera_movements)],
                "intensity": 0.7,
            },
            transition_type="crossfade",
            transition_duration_ms=500,
        )
        scenes.append(scene)
        db.add(scene)

    await db.flush()

    # Create render job
    render_job = RenderJob(
        project_id=project.id,
        render_type="final",
        status=RenderStatus.QUEUED.value,
        settings={
            "duration_seconds": request.duration_seconds,
            "voice_settings": request.voice_settings.model_dump(),
            "style_settings": request.style_settings.model_dump(),
            "scene_count": scene_count,
        },
    )

    db.add(render_job)
    await db.commit()

    # Queue the Celery task
    from app.workers.tasks.tour_video import generate_tour_video_task

    scenes_data = []
    for scene in scenes:
        photo = next((p for p in photos if p.id == scene.media_asset_id), None)
        scenes_data.append({
            "scene_id": str(scene.id),
            "sequence_order": scene.sequence_order,
            "image_url": photo.storage_url if photo else None,
            "duration_ms": scene.duration_ms,
            "camera_movement": scene.camera_movement,
            "transition_type": scene.transition_type,
        })

    # Get listing data for script generation
    listing_data = {
        "address": listing.full_address,
        "price": float(listing.listing_price) if listing.listing_price else None,
        "bedrooms": listing.bedrooms,
        "bathrooms": float(listing.bathrooms) if listing.bathrooms else None,
        "square_feet": listing.square_feet,
        "features": listing.features or [],
        "property_type": listing.property_type,
        "neighborhood": listing.neighborhood,
    }

    # Queue the task
    generate_tour_video_task.delay(
        render_job_id=str(render_job.id),
        project_id=str(project.id),
        listing_data=listing_data,
        scenes_data=scenes_data,
        voice_settings=request.voice_settings.model_dump(),
        style_settings=request.style_settings.model_dump(),
    )

    response = GenerateTourVideoResponse(
        project_id=project.id,
        render_job_id=render_job.id,
        status="queued",
        message="Tour video generation started. Check progress for updates.",
    )

    # Cache response for idempotency key (1 hour TTL)
    if x_idempotency_key:
        redis = await get_redis_for_idempotency()
        if redis:
            try:
                response_data = {
                    "project_id": str(response.project_id),
                    "render_job_id": str(response.render_job_id),
                    "status": response.status,
                    "message": response.message,
                }
                await redis.setex(
                    f"idempotency:{x_idempotency_key}",
                    3600,  # 1 hour TTL
                    json.dumps(response_data),
                )
            except Exception:
                pass  # Don't fail if caching fails

    return response


@router.get("/{project_id}/progress", response_model=TourVideoProgressResponse)
async def get_tour_video_progress(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TourVideoProgressResponse:
    """Get the progress of a tour video generation."""
    org_id = await get_user_organization_id(current_user, db)

    # Get project with render job
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id, Project.organization_id == org_id)
        .options(selectinload(Project.render_jobs))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get the most recent render job
    render_jobs = sorted(project.render_jobs, key=lambda x: x.created_at, reverse=True)
    if not render_jobs:
        raise HTTPException(status_code=404, detail="No render job found for this project")

    render_job = render_jobs[0]

    # Estimate remaining time based on progress
    estimated_remaining = None
    if render_job.status == RenderStatus.PROCESSING.value and render_job.started_at:
        elapsed = (datetime.utcnow() - render_job.started_at.replace(tzinfo=None)).total_seconds()
        if render_job.progress_percent > 0:
            total_estimated = elapsed / (render_job.progress_percent / 100)
            estimated_remaining = int(total_estimated - elapsed)

    # Parse step details from settings
    step_details = render_job.settings.get("step_progress", {})

    # Determine current step
    current_step = "queued"
    if render_job.status == RenderStatus.PROCESSING.value:
        if step_details.get("script") == "completed":
            if step_details.get("voiceover") == "completed":
                if step_details.get("videos") == "completed":
                    current_step = "compositing"
                else:
                    current_step = "generating_videos"
            else:
                current_step = "generating_voiceover"
        else:
            current_step = "generating_script"
    elif render_job.status == RenderStatus.COMPLETED.value:
        current_step = "completed"
    elif render_job.status == RenderStatus.FAILED.value:
        current_step = "failed"

    return TourVideoProgressResponse(
        project_id=project.id,
        render_job_id=render_job.id,
        status=render_job.status,
        progress_percent=render_job.progress_percent,
        current_step=current_step,
        step_details=step_details,
        estimated_remaining_seconds=estimated_remaining,
        output_url=render_job.output_url,
        error_message=render_job.error_message,
    )


@router.get("/{project_id}/preview", response_model=TourVideoPreviewResponse)
async def get_tour_video_preview(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TourVideoPreviewResponse:
    """Get a preview of the tour video with scenes and script."""
    org_id = await get_user_organization_id(current_user, db)

    # Get project with scenes
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id, Project.organization_id == org_id)
        .options(selectinload(Project.scenes))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get media assets for scenes
    media_ids = [s.media_asset_id for s in project.scenes if s.media_asset_id]
    media_map = {}
    if media_ids:
        media_result = await db.execute(
            select(MediaAsset).where(MediaAsset.id.in_(media_ids))
        )
        for media in media_result.scalars().all():
            media_map[media.id] = media

    # Build scene previews
    scenes = []
    for scene in sorted(project.scenes, key=lambda x: x.sequence_order):
        media = media_map.get(scene.media_asset_id)
        scenes.append(
            ScenePreview(
                sequence_order=scene.sequence_order,
                image_url=media.storage_url if media else "",
                narration_text=scene.narration_text,
                duration_ms=scene.duration_ms,
                camera_movement=scene.camera_movement.get("type", "zoom_in"),
            )
        )

    return TourVideoPreviewResponse(
        project_id=project.id,
        title=project.title,
        duration_seconds=project.style_settings.get("duration_seconds", 30),
        scenes=scenes,
        generated_script=project.generated_script,
        generated_caption=project.generated_caption,
        generated_hashtags=project.generated_hashtags,
    )


@router.get("/{render_job_id}/stream")
async def stream_progress(
    render_job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream real-time progress updates via Server-Sent Events.

    Connect to this endpoint to receive live updates during video generation.
    """
    org_id = await get_user_organization_id(current_user, db)

    # Verify access
    result = await db.execute(
        select(RenderJob)
        .join(Project)
        .where(
            RenderJob.id == render_job_id,
            Project.organization_id == org_id,
        )
    )
    render_job = result.scalar_one_or_none()

    if not render_job:
        raise HTTPException(status_code=404, detail="Render job not found")

    async def event_generator():
        """Generate SSE events for progress updates."""
        last_progress = -1

        while True:
            # Refresh render job from database
            await db.refresh(render_job)

            # Send update if progress changed
            if render_job.progress_percent != last_progress:
                last_progress = render_job.progress_percent

                step_progress = render_job.settings.get("step_progress", {})

                data = {
                    "status": render_job.status,
                    "progress_percent": render_job.progress_percent,
                    "step_progress": step_progress,
                    "output_url": render_job.output_url,
                    "error_message": render_job.error_message,
                }

                yield f"data: {data}\n\n"

            # Check if complete
            if render_job.status in [
                RenderStatus.COMPLETED.value,
                RenderStatus.FAILED.value,
                RenderStatus.CANCELLED.value,
            ]:
                break

            await asyncio.sleep(2)  # Poll every 2 seconds

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/{project_id}/regenerate-scene/{scene_id}")
async def regenerate_scene(
    project_id: UUID,
    scene_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Regenerate a specific scene's video."""
    org_id = await get_user_organization_id(current_user, db)

    # Verify project access
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == org_id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get the scene
    scene_result = await db.execute(
        select(Scene).where(
            Scene.id == scene_id,
            Scene.project_id == project_id,
        )
    )
    scene = scene_result.scalar_one_or_none()

    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    # Get the media asset
    media = None
    if scene.media_asset_id:
        media_result = await db.execute(
            select(MediaAsset).where(MediaAsset.id == scene.media_asset_id)
        )
        media = media_result.scalar_one_or_none()

    if not media:
        raise HTTPException(status_code=400, detail="Scene has no associated media")

    # Queue regeneration task
    from app.workers.tasks.tour_video import regenerate_scene_task

    regenerate_scene_task.delay(
        project_id=str(project_id),
        scene_id=str(scene_id),
        image_url=media.storage_url,
        camera_movement=scene.camera_movement,
        duration_ms=scene.duration_ms,
        style_settings=project.style_settings,
    )

    return {
        "status": "queued",
        "message": f"Scene {scene.sequence_order + 1} regeneration queued",
        "scene_id": str(scene_id),
    }


@router.get("/voices", response_model=list[VoiceOption])
async def list_available_voices(
    current_user: User = Depends(get_current_user),
) -> list[VoiceOption]:
    """Get list of available voices for tour video narration."""
    try:
        voices = await elevenlabs_service.get_recommended_voices()
        return [
            VoiceOption(
                voice_id=v["voice_id"],
                name=v["name"],
                label=v["label"],
                preview_url=v.get("preview_url"),
                category=v.get("category", "custom"),
            )
            for v in voices
        ]
    except Exception as e:
        # Return default voices if API fails
        return [
            VoiceOption(
                voice_id="21m00Tcm4TlvDq8ikWAM",
                name="Rachel",
                label="professional_female",
                preview_url=None,
                category="premade",
            ),
            VoiceOption(
                voice_id="29vD33N1CtxCmqQRPOHJ",
                name="Drew",
                label="professional_male",
                preview_url=None,
                category="premade",
            ),
        ]


@router.delete("/{project_id}")
async def cancel_tour_video(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel a tour video generation in progress."""
    org_id = await get_user_organization_id(current_user, db)

    result = await db.execute(
        select(Project)
        .where(Project.id == project_id, Project.organization_id == org_id)
        .options(selectinload(Project.render_jobs))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Cancel all pending/processing render jobs
    for render_job in project.render_jobs:
        if render_job.status in [RenderStatus.QUEUED.value, RenderStatus.PROCESSING.value]:
            render_job.status = RenderStatus.CANCELLED.value
            render_job.error_message = "Cancelled by user"

    project.status = "failed"

    await db.commit()

    return {
        "status": "cancelled",
        "message": "Tour video generation has been cancelled",
    }
