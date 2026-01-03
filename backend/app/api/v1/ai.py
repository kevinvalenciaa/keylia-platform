"""AI generation endpoints."""

import json
import logging
from uuid import UUID

import anthropic
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_user_organization_id
from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.project import Project, Scene
from app.models.user import User
from app.services.ai.script_generator import ScriptGeneratorService
from app.services.circuit_breaker import CircuitBreakerOpen

logger = logging.getLogger(__name__)

router = APIRouter()


# Schemas
class GenerateScriptRequest(BaseModel):
    project_id: UUID
    regenerate: bool = False


class RegenerateSceneRequest(BaseModel):
    scene_id: UUID


class GenerateCaptionRequest(BaseModel):
    project_id: UUID


class GenerateShotPlanRequest(BaseModel):
    project_id: UUID


class ScriptScene(BaseModel):
    scene_number: int
    duration_seconds: int
    narration: str
    on_screen_text: str
    suggested_photo_index: int
    emotion: str


class GeneratedScript(BaseModel):
    hook: str
    scenes: list[ScriptScene]
    cta: str
    estimated_word_count: int


class GenerateScriptResponse(BaseModel):
    script: GeneratedScript
    scenes_created: int


class GenerateCaptionResponse(BaseModel):
    caption: str
    hashtags: list[str]
    first_comment: str | None = None


# Endpoints
@router.post("/generate-script", response_model=GenerateScriptResponse)
async def generate_script(
    request: GenerateScriptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateScriptResponse:
    """Generate a full script for a video project."""
    org_id = await get_user_organization_id(current_user, db)
    
    # Get project with related data
    result = await db.execute(
        select(Project).where(
            Project.id == request.project_id,
            Project.organization_id == org_id,
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.type not in ["listing_tour", "promo_video"]:
        raise HTTPException(
            status_code=400,
            detail="Script generation is only available for video projects",
        )
    
    # Initialize script generator service
    script_service = ScriptGeneratorService()
    
    try:
        # Generate the script
        generated = await script_service.generate_script(
            project=project,
            db=db,
            regenerate=request.regenerate,
        )
        
        # Update project with generated script
        project.generated_script = generated.model_dump()
        project.status = "script_ready"
        
        # Create scene records
        scenes_created = 0
        if request.regenerate:
            # Delete existing scenes
            await db.execute(
                Scene.__table__.delete().where(Scene.project_id == project.id)
            )
        
        current_time_ms = 0
        for scene_data in generated.scenes:
            duration_ms = scene_data.duration_seconds * 1000
            scene = Scene(
                project_id=project.id,
                sequence_order=scene_data.scene_number,
                start_time_ms=current_time_ms,
                duration_ms=duration_ms,
                narration_text=scene_data.narration,
                on_screen_text=scene_data.on_screen_text,
                camera_movement={},
                transition_type="crossfade",
            )
            db.add(scene)
            current_time_ms += duration_ms
            scenes_created += 1
        
        await db.commit()
        
        return GenerateScriptResponse(
            script=generated,
            scenes_created=scenes_created,
        )
    
    except CircuitBreakerOpen as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable. Please try again in a few minutes.",
        )
    except anthropic.RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI service rate limited. Please try again shortly.",
        )
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service error. Please try again.",
        )
    except json.JSONDecodeError:
        logger.error("Failed to parse AI response as JSON")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse AI response. Please try again.",
        )
    except Exception as e:
        logger.exception(f"Unexpected error in script generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Script generation failed. Please try again.",
        )


@router.post("/regenerate-scene-text")
async def regenerate_scene_text(
    request: RegenerateSceneRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Regenerate text for a specific scene."""
    org_id = await get_user_organization_id(current_user, db)
    
    # Get scene with project
    result = await db.execute(
        select(Scene)
        .join(Project)
        .where(
            Scene.id == request.scene_id,
            Project.organization_id == org_id,
        )
    )
    scene = result.scalar_one_or_none()
    
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    
    # Get adjacent scenes for context
    result = await db.execute(
        select(Scene)
        .where(Scene.project_id == scene.project_id)
        .order_by(Scene.sequence_order)
    )
    all_scenes = result.scalars().all()
    
    script_service = ScriptGeneratorService()
    
    try:
        regenerated = await script_service.regenerate_scene(
            scene=scene,
            all_scenes=all_scenes,
            db=db,
        )
        
        # Update scene
        scene.narration_text = regenerated["narration"]
        scene.on_screen_text = regenerated["on_screen_text"]
        
        await db.commit()
        
        return {
            "scene_id": str(scene.id),
            "narration": regenerated["narration"],
            "on_screen_text": regenerated["on_screen_text"],
            "emotion": regenerated.get("emotion"),
        }
    
    except CircuitBreakerOpen:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable. Please try again in a few minutes.",
        )
    except anthropic.RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI service rate limited. Please try again shortly.",
        )
    except Exception as e:
        logger.exception(f"Unexpected error in scene regeneration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Scene regeneration failed. Please try again.",
        )


@router.post("/generate-caption", response_model=GenerateCaptionResponse)
async def generate_caption(
    request: GenerateCaptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateCaptionResponse:
    """Generate social media caption and hashtags."""
    org_id = await get_user_organization_id(current_user, db)
    
    result = await db.execute(
        select(Project).where(
            Project.id == request.project_id,
            Project.organization_id == org_id,
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    script_service = ScriptGeneratorService()
    
    try:
        caption_data = await script_service.generate_caption(project=project, db=db)
        
        # Update project
        project.generated_caption = caption_data["caption"]
        project.generated_hashtags = caption_data["hashtags"]
        
        await db.commit()
        
        return GenerateCaptionResponse(
            caption=caption_data["caption"],
            hashtags=caption_data["hashtags"],
            first_comment=caption_data.get("first_comment"),
        )
    
    except CircuitBreakerOpen:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable. Please try again in a few minutes.",
        )
    except anthropic.RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI service rate limited. Please try again shortly.",
        )
    except Exception as e:
        logger.exception(f"Unexpected error in caption generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Caption generation failed. Please try again.",
        )


@router.post("/generate-shot-plan")
async def generate_shot_plan(
    request: GenerateShotPlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate camera movements for all scenes."""
    org_id = await get_user_organization_id(current_user, db)
    
    result = await db.execute(
        select(Project).where(
            Project.id == request.project_id,
            Project.organization_id == org_id,
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get scenes
    result = await db.execute(
        select(Scene)
        .where(Scene.project_id == project.id)
        .order_by(Scene.sequence_order)
    )
    scenes = result.scalars().all()
    
    if not scenes:
        raise HTTPException(status_code=400, detail="No scenes found for project")
    
    script_service = ScriptGeneratorService()
    
    try:
        shot_plan = await script_service.generate_shot_plan(
            project=project,
            scenes=scenes,
            db=db,
        )
        
        # Update scenes with camera movements
        for scene_plan in shot_plan["scenes"]:
            scene_num = scene_plan["scene_number"]
            if scene_num <= len(scenes):
                scene = scenes[scene_num - 1]
                scene.camera_movement = scene_plan["movement"]
                if "transition_to_next" in scene_plan:
                    scene.transition_type = scene_plan["transition_to_next"]["type"]
                    scene.transition_duration_ms = scene_plan["transition_to_next"]["duration_ms"]
        
        await db.commit()
        
        return {
            "scenes_updated": len(shot_plan["scenes"]),
            "shot_plan": shot_plan,
        }
    
    except CircuitBreakerOpen:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable. Please try again in a few minutes.",
        )
    except anthropic.RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI service rate limited. Please try again shortly.",
        )
    except Exception as e:
        logger.exception(f"Unexpected error in shot plan generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Shot plan generation failed. Please try again.",
        )

