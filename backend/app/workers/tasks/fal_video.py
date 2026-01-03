"""fal.ai video generation tasks."""

import asyncio
from typing import Any

from app.workers.celery_app import celery_app
from app.services.ai.fal_video_service import (
    FalVideoService,
    FalVideoServiceAsync,
    VideoGenerationRequest,
    VideoModel,
    CameraMotion,
)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="fal_generate_video")
def fal_generate_video_task(
    self,
    image_url: str,
    prompt: str = "",
    duration_seconds: float = 5.0,
    camera_motion: str = "zoom_in",
    tone: str = "modern",
    model: str = "kling",
) -> dict[str, Any]:
    """
    Generate a video from an image using fal.ai.
    
    Args:
        image_url: URL of the source image
        prompt: Optional text prompt to guide generation
        duration_seconds: Video duration (5 or 10 seconds typically)
        camera_motion: Type of camera movement
        tone: Style tone (luxury, modern, cozy, etc.)
        model: Which fal.ai model to use
    
    Returns:
        Dict with video_url and metadata
    """
    try:
        self.update_state(state="PROGRESS", meta={"percent": 10, "step": "Initializing fal.ai"})
        
        fal_service = FalVideoService()
        
        # Map model string to enum
        model_map = {
            "kling": VideoModel.KLING_STANDARD,
            "kling_pro": VideoModel.KLING_PRO,
            "luma": VideoModel.LUMA_DREAM,
            "runway": VideoModel.RUNWAY_GEN3,
            "stable_video": VideoModel.STABLE_VIDEO,
            "fast": VideoModel.FAST_SVD_LCM,
            "minimax": VideoModel.MINIMAX,
        }
        video_model = model_map.get(model, VideoModel.KLING_STANDARD)
        
        # Map camera motion string to enum
        motion_map = {
            "zoom_in": CameraMotion.ZOOM_IN,
            "zoom_out": CameraMotion.ZOOM_OUT,
            "pan_left": CameraMotion.PAN_LEFT,
            "pan_right": CameraMotion.PAN_RIGHT,
            "pan_up": CameraMotion.PAN_UP,
            "pan_down": CameraMotion.PAN_DOWN,
            "static": CameraMotion.STATIC,
            "orbit_left": CameraMotion.ORBIT_LEFT,
            "orbit_right": CameraMotion.ORBIT_RIGHT,
        }
        cam_motion = motion_map.get(camera_motion, CameraMotion.ZOOM_IN)
        
        self.update_state(state="PROGRESS", meta={"percent": 20, "step": "Generating video"})
        
        # Build request
        request = VideoGenerationRequest(
            image_url=image_url,
            prompt=prompt if prompt else None,
            duration_seconds=duration_seconds,
            motion_intensity=0.6 if tone == "calm" else 0.75,
            camera_motion=cam_motion,
            model=video_model,
        )
        
        # Generate video
        result = run_async(fal_service.generate_video_from_image(request))
        
        self.update_state(state="PROGRESS", meta={"percent": 100, "step": "Complete"})
        
        return {
            "video_url": result.video_url,
            "duration_seconds": result.duration_seconds,
            "width": result.width,
            "height": result.height,
            "seed": result.seed,
        }
    
    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="fal_generate_property_tour")
def fal_generate_property_tour_task(
    self,
    scenes: list[dict[str, Any]],
    style_settings: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate all video clips for a property tour using fal.ai.
    
    Args:
        scenes: List of scene data with image_url, narration, camera_movement
        style_settings: Style preferences (tone, pace, etc.)
    
    Returns:
        Dict with list of generated video URLs
    """
    try:
        self.update_state(state="PROGRESS", meta={"percent": 5, "step": "Starting generation"})
        
        fal_service = FalVideoService()
        total_scenes = len(scenes)
        generated_videos = []
        
        for i, scene in enumerate(scenes):
            progress = 5 + int((i / total_scenes) * 90)
            self.update_state(
                state="PROGRESS",
                meta={"percent": progress, "step": f"Generating scene {i+1}/{total_scenes}"}
            )
            
            result = run_async(
                fal_service.generate_scene_video(
                    image_url=scene["image_url"],
                    narration_text=scene.get("narration_text", ""),
                    camera_movement=scene.get("camera_movement", {"type": "zoom_in"}),
                    duration_seconds=scene.get("duration_seconds", 5.0),
                    tone=style_settings.get("tone", "modern"),
                )
            )
            
            generated_videos.append({
                "scene_number": i + 1,
                "video_url": result.video_url,
                "duration_seconds": result.duration_seconds,
                "width": result.width,
                "height": result.height,
            })
        
        self.update_state(state="PROGRESS", meta={"percent": 100, "step": "All scenes generated"})
        
        return {
            "scenes": generated_videos,
            "total_duration": sum(v["duration_seconds"] for v in generated_videos),
            "scene_count": len(generated_videos),
        }
    
    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="fal_submit_async")
def fal_submit_async_task(
    self,
    model: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """
    Submit a video generation job to fal.ai asynchronously.
    
    Returns the request ID for polling status.
    """
    try:
        fal_service = FalVideoServiceAsync()
        
        request_id = run_async(
            fal_service.generate_video_async(model, arguments)
        )
        
        return {
            "request_id": request_id,
            "model": model,
            "status": "submitted",
        }
    
    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="fal_check_status")
def fal_check_status_task(self, model: str, request_id: str) -> dict[str, Any]:
    """Check the status of an async fal.ai job."""
    try:
        fal_service = FalVideoServiceAsync()
        
        status = run_async(fal_service.get_job_status(model, request_id))
        
        return {
            "request_id": request_id,
            "status": status["status"],
            "logs": status.get("logs", []),
        }
    
    except Exception as e:
        return {
            "request_id": request_id,
            "status": "error",
            "error": str(e),
        }


@celery_app.task(bind=True, name="fal_get_result")
def fal_get_result_task(self, model: str, request_id: str) -> dict[str, Any]:
    """Get the result of a completed fal.ai job."""
    try:
        fal_service = FalVideoServiceAsync()
        
        result = run_async(fal_service.get_job_result(model, request_id))
        
        return {
            "request_id": request_id,
            "status": "completed",
            "result": result,
        }
    
    except Exception as e:
        return {
            "request_id": request_id,
            "status": "error",
            "error": str(e),
        }

