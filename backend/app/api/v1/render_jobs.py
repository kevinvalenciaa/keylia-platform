"""Render job endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.api.v1.projects import get_user_organization_id
from app.database import get_db
from app.models.project import Project, Scene
from app.models.render import RenderJob, RenderStatus, RenderType
from app.models.user import User
from app.workers.tasks.fal_video import fal_generate_video_task
from app.workers.tasks.render_video import render_video_task

router = APIRouter()


class RenderRequest(BaseModel):
    render_type: str = "final"  # preview, final
    settings: dict[str, Any] = {}


class VideoGenerationRequest(BaseModel):
    image_url: str
    prompt: str = ""
    duration_seconds: float = 5.0
    camera_motion: str = "zoom_in"
    tone: str = "modern"
    model: str = "kling"


class RenderJobResponse(BaseModel):
    id: UUID
    project_id: UUID
    render_type: str
    status: str
    progress_percent: int
    output_url: str | None
    error_message: str | None

    class Config:
        from_attributes = True


@router.post("/projects/{project_id}/renders", response_model=RenderJobResponse)
async def create_render_job(
    project_id: UUID,
    request: RenderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RenderJobResponse:
    """Start a new render job for a project using fal.ai video generation."""
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
    
    # Get scenes
    result = await db.execute(
        select(Scene)
        .where(Scene.project_id == project_id)
        .order_by(Scene.sequence_order)
    )
    scenes = result.scalars().all()
    
    if not scenes:
        raise HTTPException(status_code=400, detail="No scenes found for project")
    
    # Create render job record
    render_job = RenderJob(
        project_id=project_id,
        render_type=request.render_type,
        settings=request.settings,
        status=RenderStatus.QUEUED.value,
    )
    db.add(render_job)
    await db.commit()
    await db.refresh(render_job)
    
    # Prepare scene data for worker
    scenes_data = []
    for scene in scenes:
        scene_data = {
            "image_url": scene.media_asset.storage_url if scene.media_asset else "",
            "narration_text": scene.narration_text or "",
            "on_screen_text": scene.on_screen_text or "",
            "camera_movement": scene.camera_movement or {"type": "zoom_in"},
            "duration_ms": scene.duration_ms,
            "tone": project.style_settings.get("tone", "modern"),
            "voice_enabled": project.voice_settings.get("enabled", True),
            "voice_settings": project.voice_settings,
            "overlay_settings": scene.overlay_settings,
        }
        scenes_data.append(scene_data)
    
    # Queue render task
    render_video_task.delay(
        render_job_id=str(render_job.id),
        project_id=str(project_id),
        scenes_data=scenes_data,
    )
    
    return RenderJobResponse(
        id=render_job.id,
        project_id=render_job.project_id,
        render_type=render_job.render_type,
        status=render_job.status,
        progress_percent=render_job.progress_percent,
        output_url=render_job.output_url,
        error_message=render_job.error_message,
    )


@router.get("/{render_id}", response_model=RenderJobResponse)
async def get_render_job(
    render_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RenderJobResponse:
    """Get render job status."""
    org_id = await get_user_organization_id(current_user, db)
    
    result = await db.execute(
        select(RenderJob)
        .join(Project)
        .where(
            RenderJob.id == render_id,
            Project.organization_id == org_id,
        )
    )
    render_job = result.scalar_one_or_none()
    
    if not render_job:
        raise HTTPException(status_code=404, detail="Render job not found")
    
    return RenderJobResponse(
        id=render_job.id,
        project_id=render_job.project_id,
        render_type=render_job.render_type,
        status=render_job.status,
        progress_percent=render_job.progress_percent,
        output_url=render_job.output_url,
        error_message=render_job.error_message,
    )


@router.post("/generate-video")
async def generate_single_video(
    request: VideoGenerationRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Generate a single video clip from an image using fal.ai.
    
    This endpoint is useful for testing and previewing video generation
    before creating a full project render.
    """
    # Queue the task
    task = fal_generate_video_task.delay(
        image_url=request.image_url,
        prompt=request.prompt,
        duration_seconds=request.duration_seconds,
        camera_motion=request.camera_motion,
        tone=request.tone,
        model=request.model,
    )
    
    return {
        "task_id": task.id,
        "status": "queued",
        "message": "Video generation started. Poll the task status for updates.",
    }


@router.get("/task/{task_id}/status")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the status of a Celery task."""
    from app.workers.celery_app import celery_app
    
    result = celery_app.AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": result.status,
    }
    
    if result.status == "PROGRESS":
        response["progress"] = result.info
    elif result.status == "SUCCESS":
        response["result"] = result.result
    elif result.status == "FAILURE":
        response["error"] = str(result.result)
    
    return response

