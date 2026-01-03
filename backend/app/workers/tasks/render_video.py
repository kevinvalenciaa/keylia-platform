"""Video rendering task using fal.ai for AI video generation."""

import asyncio
import tempfile
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx

from app.workers.celery_app import celery_app
from app.services.ai.fal_video_service import FalVideoService, VideoGenerationRequest, VideoModel


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="render_video")
def render_video_task(self, render_job_id: str, project_id: str, scenes_data: list[dict]) -> dict:
    """
    Render a video from project scenes using fal.ai.
    
    Steps:
    1. Load project and scenes data
    2. Generate video clips for each scene using fal.ai
    3. Generate voiceover audio using ElevenLabs
    4. Concatenate video clips with FFmpeg
    5. Add text overlays and graphics
    6. Mix audio (voiceover + music)
    7. Upload final video to S3
    8. Update render job status
    """
    try:
        self.update_state(state="PROGRESS", meta={"percent": 5, "step": "Initializing"})
        
        fal_service = FalVideoService()
        generated_clips = []
        total_scenes = len(scenes_data)
        
        # Step 1: Generate video clips for each scene using fal.ai
        self.update_state(state="PROGRESS", meta={"percent": 10, "step": "Generating video scenes with AI"})
        
        for i, scene in enumerate(scenes_data):
            progress = 10 + int((i / total_scenes) * 50)
            self.update_state(
                state="PROGRESS", 
                meta={"percent": progress, "step": f"Generating scene {i+1}/{total_scenes}"}
            )
            
            # Generate video from image using fal.ai
            result = run_async(
                fal_service.generate_scene_video(
                    image_url=scene["image_url"],
                    narration_text=scene.get("narration_text", ""),
                    camera_movement=scene.get("camera_movement", {"type": "zoom_in"}),
                    duration_seconds=scene.get("duration_ms", 5000) / 1000,
                    tone=scene.get("tone", "modern"),
                )
            )
            
            generated_clips.append({
                "scene_number": i + 1,
                "video_url": result.video_url,
                "duration": result.duration_seconds,
            })
        
        self.update_state(state="PROGRESS", meta={"percent": 60, "step": "Processing audio"})
        
        # Step 2: Generate voiceover (if enabled)
        voiceover_url = None
        if scenes_data and scenes_data[0].get("voice_enabled", True):
            full_narration = " ".join([s.get("narration_text", "") for s in scenes_data])
            voiceover_result = run_async(
                generate_voiceover_async(full_narration, scenes_data[0].get("voice_settings", {}))
            )
            voiceover_url = voiceover_result.get("audio_url")
        
        self.update_state(state="PROGRESS", meta={"percent": 70, "step": "Compositing final video"})
        
        # Step 3: Concatenate clips and add audio using FFmpeg
        final_video_url = run_async(
            composite_final_video(
                clips=generated_clips,
                voiceover_url=voiceover_url,
                music_url=scenes_data[0].get("music_url") if scenes_data else None,
                overlay_settings=scenes_data[0].get("overlay_settings", {}) if scenes_data else {},
            )
        )
        
        self.update_state(state="PROGRESS", meta={"percent": 90, "step": "Uploading to storage"})
        
        # Step 4: Upload to S3 and get final URL
        # (In production, composite_final_video would handle S3 upload)
        
        self.update_state(state="PROGRESS", meta={"percent": 100, "step": "Complete"})
        
        return {
            "render_job_id": render_job_id,
            "project_id": project_id,
            "output_url": final_video_url,
            "subtitle_url": f"{final_video_url.rsplit('.', 1)[0]}.srt",
            "duration_seconds": sum(c["duration"] for c in generated_clips),
            "file_size_bytes": 0,  # Will be updated after S3 upload
            "scenes_generated": len(generated_clips),
        }
    
    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="generate_scene_clip")
def generate_scene_clip_task(
    self,
    image_url: str,
    camera_movement: dict,
    duration_seconds: float = 5.0,
    tone: str = "modern",
) -> dict:
    """Generate a single video clip from an image using fal.ai."""
    try:
        fal_service = FalVideoService()
        
        result = run_async(
            fal_service.generate_scene_video(
                image_url=image_url,
                narration_text="",
                camera_movement=camera_movement,
                duration_seconds=duration_seconds,
                tone=tone,
            )
        )
        
        return {
            "video_url": result.video_url,
            "duration_seconds": result.duration_seconds,
            "width": result.width,
            "height": result.height,
        }
    
    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="generate_preview")
def generate_preview_task(self, render_job_id: str, project_id: str, scenes_data: list[dict]) -> dict:
    """
    Generate a low-resolution quick preview using fal.ai's fastest model.
    """
    try:
        self.update_state(state="PROGRESS", meta={"percent": 10, "step": "Generating preview"})
        
        fal_service = FalVideoService()
        
        # Only generate first 2-3 scenes for preview
        preview_scenes = scenes_data[:3] if len(scenes_data) > 3 else scenes_data
        
        clips = []
        for i, scene in enumerate(preview_scenes):
            result = run_async(
                fal_service.generate_video_from_image(
                    VideoGenerationRequest(
                        image_url=scene["image_url"],
                        duration_seconds=3.0,  # Shorter duration for preview
                        motion_intensity=0.5,
                        model=VideoModel.FAST_SVD_LCM,  # Fastest model for preview
                    )
                )
            )
            clips.append(result.video_url)
        
        self.update_state(state="PROGRESS", meta={"percent": 100, "step": "Preview ready"})
        
        # Return first clip as preview (or concatenate if needed)
        return {
            "render_job_id": render_job_id,
            "output_url": clips[0] if clips else None,
            "is_preview": True,
        }
    
    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise


# Helper async functions

async def generate_voiceover_async(text: str, voice_settings: dict) -> dict:
    """Generate voiceover using ElevenLabs (placeholder)."""
    # TODO: Implement ElevenLabs integration
    return {"audio_url": None}


async def composite_final_video(
    clips: list[dict],
    voiceover_url: str | None,
    music_url: str | None,
    overlay_settings: dict,
) -> str:
    """
    Composite final video from clips using FFmpeg.
    
    This downloads all clips, concatenates them, adds audio, and uploads to S3.
    """
    # TODO: Implement FFmpeg composition
    # For now, return the first clip as the "final" video
    if clips:
        return clips[0]["video_url"]
    return ""

