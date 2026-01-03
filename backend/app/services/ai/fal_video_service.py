"""fal.ai video generation service."""

import asyncio
import logging
from enum import Enum
from typing import Any, Optional

import fal_client
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class VideoModel(str, Enum):
    """Available fal.ai video models."""

    # Stable Video Diffusion - good for image-to-video
    STABLE_VIDEO = "fal-ai/stable-video"

    # Fast SVD with LCM - faster generation
    FAST_SVD_LCM = "fal-ai/fast-svd-lcm"

    # Kling - high quality cinematic video
    KLING_STANDARD = "fal-ai/kling-video/v1/standard/image-to-video"
    KLING_PRO = "fal-ai/kling-video/v1/pro/image-to-video"
    KLING_V2_PRO = "fal-ai/kling-video/v2.6/pro/image-to-video"  # Latest cinematic

    # Luma Dream Machine - smooth motion
    LUMA_DREAM = "fal-ai/luma-dream-machine"

    # Runway Gen-3 - text-to-video
    RUNWAY_GEN3 = "fal-ai/runway-gen3/turbo/image-to-video"

    # MiniMax - longer videos, cinematic colors
    MINIMAX = "fal-ai/minimax/video-01/image-to-video"

    # Veo 3.1 - Google's most realistic
    VEO_3 = "fal-ai/veo3.1/image-to-video"
    VEO_3_FAST = "fal-ai/veo3.1/fast/image-to-video"


class CameraMotion(str, Enum):
    """Camera motion presets for video generation."""
    
    ZOOM_IN = "zoom in"
    ZOOM_OUT = "zoom out"
    PAN_LEFT = "pan left"
    PAN_RIGHT = "pan right"
    PAN_UP = "tilt up"
    PAN_DOWN = "tilt down"
    STATIC = "static"
    ORBIT_LEFT = "orbit left"
    ORBIT_RIGHT = "orbit right"


class VideoGenerationRequest(BaseModel):
    """Request for video generation."""
    
    image_url: str
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    duration_seconds: float = 5.0
    motion_intensity: float = 0.7  # 0.0 to 1.0
    camera_motion: Optional[CameraMotion] = None
    seed: Optional[int] = None
    model: VideoModel = VideoModel.KLING_PRO


class VideoGenerationResult(BaseModel):
    """Result from video generation."""
    
    video_url: str
    duration_seconds: float
    width: int
    height: int
    seed: Optional[int] = None


class FalVideoService:
    """Service for generating videos using fal.ai."""

    def __init__(self):
        # Set the fal.ai API key
        import os
        os.environ["FAL_KEY"] = settings.FAL_KEY

    async def generate_video_from_image(
        self,
        request: VideoGenerationRequest,
    ) -> VideoGenerationResult:
        """
        Generate a video from a static image using fal.ai.
        
        This creates smooth Ken Burns-style motion from property photos.
        """
        
        # Build the prompt for camera motion
        motion_prompt = self._build_motion_prompt(request)
        
        # Select the appropriate model and build arguments
        model_args = self._build_model_args(request, motion_prompt)
        
        # Submit to fal.ai
        result = await self._run_fal_model(request.model.value, model_args)
        
        return VideoGenerationResult(
            video_url=result["video"]["url"],
            duration_seconds=request.duration_seconds,
            width=result.get("video", {}).get("width", 1080),
            height=result.get("video", {}).get("height", 1920),
            seed=result.get("seed"),
        )

    async def generate_scene_video(
        self,
        image_url: str,
        narration_text: str,
        camera_movement: dict[str, Any],
        duration_seconds: float = 5.0,
        tone: str = "modern",
    ) -> VideoGenerationResult:
        """
        Generate a video scene from an image with specific camera movement.
        
        This is used to create individual scenes for property tours.
        """
        
        # Map camera movement to fal.ai motion type
        movement_type = camera_movement.get("type", "zoom_in")
        camera_motion = self._map_camera_motion(movement_type)
        
        # Build a cinematic prompt based on the narration and tone
        prompt = self._build_cinematic_prompt(narration_text, tone)
        
        request = VideoGenerationRequest(
            image_url=image_url,
            prompt=prompt,
            duration_seconds=duration_seconds,
            motion_intensity=0.6 if tone == "calm" else 0.75,
            camera_motion=camera_motion,
            model=VideoModel.KLING_PRO,
        )
        
        return await self.generate_video_from_image(request)

    async def generate_property_tour(
        self,
        scene_images: list[dict[str, Any]],
        style_settings: dict[str, Any],
    ) -> list[VideoGenerationResult]:
        """
        Generate all video clips for a property tour.
        
        Each scene is processed in parallel for faster generation.
        """
        
        tasks = []
        for scene in scene_images:
            task = self.generate_scene_video(
                image_url=scene["image_url"],
                narration_text=scene.get("narration", ""),
                camera_movement=scene.get("camera_movement", {}),
                duration_seconds=scene.get("duration", 5.0),
                tone=style_settings.get("tone", "modern"),
            )
            tasks.append(task)
        
        # Run all scene generations in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out any failed generations
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Scene {i} generation failed: {result}")
            else:
                successful_results.append(result)
        
        return successful_results

    def _build_motion_prompt(self, request: VideoGenerationRequest) -> str:
        """Build a motion description prompt."""
        
        base_prompt = request.prompt or "cinematic real estate property video"
        
        if request.camera_motion:
            motion_desc = {
                CameraMotion.ZOOM_IN: "slowly zooming in, revealing details",
                CameraMotion.ZOOM_OUT: "slowly zooming out, revealing the full space",
                CameraMotion.PAN_LEFT: "smooth panning left across the space",
                CameraMotion.PAN_RIGHT: "smooth panning right across the space",
                CameraMotion.PAN_UP: "tilting up to reveal height and grandeur",
                CameraMotion.PAN_DOWN: "tilting down in a welcoming motion",
                CameraMotion.STATIC: "subtle ambient motion, stable camera",
                CameraMotion.ORBIT_LEFT: "slowly orbiting left around the subject",
                CameraMotion.ORBIT_RIGHT: "slowly orbiting right around the subject",
            }
            motion = motion_desc.get(request.camera_motion, "smooth cinematic motion")
            return f"{base_prompt}, {motion}"
        
        return base_prompt

    def _build_model_args(
        self,
        request: VideoGenerationRequest,
        motion_prompt: str,
    ) -> dict[str, Any]:
        """Build model-specific arguments."""
        
        model = request.model
        
        if model in [VideoModel.KLING_STANDARD, VideoModel.KLING_PRO, VideoModel.KLING_V2_PRO]:
            return {
                "prompt": motion_prompt,
                "image_url": request.image_url,
                "duration": "5" if request.duration_seconds <= 5 else "10",
                "aspect_ratio": "9:16",  # Vertical for social media
            }

        elif model in [VideoModel.VEO_3, VideoModel.VEO_3_FAST]:
            return {
                "prompt": motion_prompt,
                "image_url": request.image_url,
                "aspect_ratio": "9:16",
                "duration": "6s" if request.duration_seconds <= 6 else "8s",
            }

        elif model == VideoModel.LUMA_DREAM:
            return {
                "prompt": motion_prompt,
                "image_url": request.image_url,
                "aspect_ratio": "9:16",
            }
        
        elif model == VideoModel.RUNWAY_GEN3:
            return {
                "prompt": motion_prompt,
                "image_url": request.image_url,
                "duration": 5 if request.duration_seconds <= 5 else 10,
                "ratio": "9:16",
            }
        
        elif model == VideoModel.MINIMAX:
            return {
                "prompt": motion_prompt,
                "image_url": request.image_url,
            }
        
        elif model in [VideoModel.STABLE_VIDEO, VideoModel.FAST_SVD_LCM]:
            return {
                "image_url": request.image_url,
                "motion_bucket_id": int(request.motion_intensity * 255),
                "fps": 25,
                "seed": request.seed,
            }
        
        # Default fallback
        return {
            "prompt": motion_prompt,
            "image_url": request.image_url,
        }

    def _map_camera_motion(self, movement_type: str) -> CameraMotion:
        """Map internal camera movement types to fal.ai motion types."""
        
        mapping = {
            "zoom_in": CameraMotion.ZOOM_IN,
            "zoom_out": CameraMotion.ZOOM_OUT,
            "pan_left": CameraMotion.PAN_LEFT,
            "pan_right": CameraMotion.PAN_RIGHT,
            "pan_up": CameraMotion.PAN_UP,
            "pan_down": CameraMotion.PAN_DOWN,
            "static": CameraMotion.STATIC,
            "orbit_left": CameraMotion.ORBIT_LEFT,
            "orbit_right": CameraMotion.ORBIT_RIGHT,
            "ken_burns": CameraMotion.ZOOM_IN,  # Default Ken Burns to zoom in
        }
        
        return mapping.get(movement_type, CameraMotion.ZOOM_IN)

    def _build_cinematic_prompt(self, narration: str, tone: str) -> str:
        """Build a cinematic prompt for the video generation."""
        
        tone_modifiers = {
            "luxury": "luxurious, elegant, high-end real estate, warm lighting, cinematic",
            "cozy": "warm, inviting, cozy home, soft natural lighting, comfortable",
            "modern": "modern, sleek, contemporary design, clean lines, bright",
            "minimal": "minimalist, clean, simple, serene, natural light",
            "bold": "dramatic, bold, striking, high contrast, dynamic",
        }
        
        modifier = tone_modifiers.get(tone, tone_modifiers["modern"])
        
        # Extract key subjects from narration for better video generation
        prompt = f"cinematic real estate video, {modifier}, smooth camera motion, professional quality, 4K"
        
        return prompt

    async def _run_fal_model(
        self,
        model: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Run a fal.ai model and wait for results."""
        
        def submit_and_wait():
            """Synchronous function to run in executor."""
            handler = fal_client.submit(model, arguments=arguments)
            result = handler.get()
            return result
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, submit_and_wait)
        
        return result


# Alternative async implementation using queue
class FalVideoServiceAsync:
    """Async version using fal.ai queue for long-running jobs."""

    def __init__(self):
        import os
        os.environ["FAL_KEY"] = settings.FAL_KEY

    async def generate_video_async(
        self,
        model: str,
        arguments: dict[str, Any],
        webhook_url: Optional[str] = None,
    ) -> str:
        """
        Submit a video generation job and return the request ID.
        
        Use this for long-running jobs where you want to poll for status.
        """
        
        def submit():
            handler = fal_client.submit(model, arguments=arguments)
            return handler.request_id
        
        loop = asyncio.get_event_loop()
        request_id = await loop.run_in_executor(None, submit)
        
        return request_id

    async def get_job_status(self, model: str, request_id: str) -> dict[str, Any]:
        """Get the status of a video generation job."""
        
        def get_status():
            return fal_client.status(model, request_id, with_logs=True)
        
        loop = asyncio.get_event_loop()
        status = await loop.run_in_executor(None, get_status)
        
        return {
            "status": status.status,
            "logs": getattr(status, "logs", []),
        }

    async def get_job_result(self, model: str, request_id: str) -> dict[str, Any]:
        """Get the result of a completed video generation job."""
        
        def get_result():
            return fal_client.result(model, request_id)
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, get_result)
        
        return result

