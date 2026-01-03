"""Tour video generation Celery tasks."""

import asyncio
import io
import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any
from uuid import UUID

import boto3
import httpx
from botocore.config import Config as BotoConfig
from sqlalchemy.orm import Session

from app.config import settings
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Maximum parallel video generations
MAX_PARALLEL_VIDEO_GENERATIONS = 5


def get_sync_db():
    """Get synchronous database session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Convert async URL to sync
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(sync_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def update_render_job(db: Session, render_job_id: str, **kwargs):
    """Update render job status."""
    from app.models.render import RenderJob

    render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
    if render_job:
        for key, value in kwargs.items():
            setattr(render_job, key, value)
        db.commit()
        db.refresh(render_job)
    return render_job


def update_step_progress(db: Session, render_job_id: str, step: str, status: str, details: dict = None):
    """Update step progress in render job settings."""
    from app.models.render import RenderJob

    render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
    if render_job:
        step_progress = render_job.settings.get("step_progress", {})
        step_progress[step] = {"status": status, **(details or {})}
        render_job.settings = {**render_job.settings, "step_progress": step_progress}
        db.commit()
    return render_job


@celery_app.task(
    bind=True,
    name="generate_tour_video",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def generate_tour_video_task(
    self,
    render_job_id: str,
    project_id: str,
    listing_data: dict,
    scenes_data: list[dict],
    voice_settings: dict,
    style_settings: dict,
) -> dict:
    """
    Main orchestration task for tour video generation.

    Pipeline:
    1. Generate script from listing data (OpenAI)
    2. Generate voiceover from script (ElevenLabs)
    3. Generate video clips for each scene (fal.ai)
    4. Composite final video with audio (FFmpeg)
    5. Upload to S3
    6. Update render job status
    """
    db = get_sync_db()

    try:
        # Mark as processing
        update_render_job(
            db,
            render_job_id,
            status="processing",
            started_at=datetime.utcnow(),
            progress_percent=5,
            worker_id=self.request.id,
        )

        # Step 1: Generate script (10%)
        update_step_progress(db, render_job_id, "script", "in_progress")
        script_result = generate_script_sync(listing_data, scenes_data, style_settings)
        update_step_progress(db, render_job_id, "script", "completed", {"scenes": len(script_result["scenes"])})
        update_render_job(db, render_job_id, progress_percent=15)

        # Update scenes with narration
        update_scenes_with_script(db, project_id, script_result["scenes"])

        # Step 2 & 3: Generate voiceover AND video clips IN PARALLEL
        # This is the main optimization - both can run simultaneously
        update_step_progress(db, render_job_id, "voiceover", "in_progress")
        update_step_progress(db, render_job_id, "videos", "in_progress", {"completed": 0, "total": len(scenes_data)})
        update_render_job(db, render_job_id, progress_percent=20)

        # Combine hook + scene narrations + call to action for full voiceover
        hook = script_result.get("hook", "")
        scene_narrations = " ".join([s["narration"] for s in script_result["scenes"]])
        cta = script_result.get("cta", "")

        # Build full narration with all parts
        narration_parts = [hook, scene_narrations, cta]
        full_narration = " ".join(part for part in narration_parts if part)

        # Use ThreadPoolExecutor for parallel execution
        voiceover_result = None
        video_clips = [None] * len(scenes_data)
        completed_count = 0

        def generate_voiceover_wrapper():
            return generate_voiceover_sync(full_narration, voice_settings)

        def generate_clip_wrapper(idx, scene, scene_script):
            return idx, generate_scene_clip_sync(
                image_url=scene["image_url"],
                narration=scene_script.get("narration", ""),
                camera_movement=scene["camera_movement"],
                duration_ms=scene["duration_ms"],
                style_settings=style_settings,
            )

        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_VIDEO_GENERATIONS + 1) as executor:
            futures = []

            # Submit voiceover generation
            voiceover_future = executor.submit(generate_voiceover_wrapper)
            futures.append(("voiceover", voiceover_future))

            # Submit ALL video clips in parallel
            for i, scene in enumerate(scenes_data):
                scene_script = script_result["scenes"][i] if i < len(script_result["scenes"]) else {}
                video_future = executor.submit(generate_clip_wrapper, i, scene, scene_script)
                futures.append(("video", video_future))

            # Process results as they complete
            for future_type, future in futures:
                try:
                    if future_type == "voiceover":
                        voiceover_result = future.result()
                        update_step_progress(db, render_job_id, "voiceover", "completed", {
                            "duration_seconds": voiceover_result.get("duration_seconds"),
                        })
                    else:
                        idx, clip_result = future.result()
                        video_clips[idx] = clip_result
                        completed_count += 1
                        progress = 20 + int(completed_count / len(scenes_data) * 55)
                        update_step_progress(db, render_job_id, "videos", "in_progress", {
                            "completed": completed_count,
                            "total": len(scenes_data),
                        })
                        update_render_job(db, render_job_id, progress_percent=progress)
                except Exception as e:
                    raise Exception(f"Failed during parallel generation: {str(e)}")

        update_step_progress(db, render_job_id, "videos", "completed")

        # Step 4: Composite final video (75% - 90%)
        update_step_progress(db, render_job_id, "composition", "in_progress")
        final_video_path = composite_video_sync(
            video_clips=video_clips,
            voiceover_data=voiceover_result.get("audio_data"),
            style_settings=style_settings,
        )
        update_step_progress(db, render_job_id, "composition", "completed")
        update_render_job(db, render_job_id, progress_percent=90)

        # Step 5: Upload to S3 (90% - 100%)
        update_step_progress(db, render_job_id, "upload", "in_progress")
        output_url, file_size = upload_to_storage(final_video_path, project_id)
        update_step_progress(db, render_job_id, "upload", "completed")

        # Update project with generated content
        update_project_content(
            db,
            project_id,
            script=script_result,
            caption=script_result.get("caption", ""),
            hashtags=script_result.get("hashtags", []),
        )

        # Mark as completed
        update_render_job(
            db,
            render_job_id,
            status="completed",
            completed_at=datetime.utcnow(),
            progress_percent=100,
            output_url=output_url,
            output_file_size=file_size,
        )

        # Cleanup temp file
        if os.path.exists(final_video_path):
            os.remove(final_video_path)

        return {
            "status": "completed",
            "output_url": output_url,
            "file_size": file_size,
        }

    except Exception as e:
        update_render_job(
            db,
            render_job_id,
            status="failed",
            error_message=str(e),
            error_details={"exception": type(e).__name__},
        )
        raise

    finally:
        db.close()


def generate_script_sync(listing_data: dict, scenes_data: list, style_settings: dict) -> dict:
    """Generate script using Anthropic Claude."""
    import anthropic
    import json
    import re

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    scene_count = len(scenes_data)
    tone = style_settings.get("tone", "modern")
    duration_seconds = style_settings.get("duration_seconds", 30)

    # Calculate optimal word counts based on duration
    # Social media voiceover pace: ~2.5 words/second
    # Leave room for pauses and pacing
    duration_config = {
        15: {"total_words": 35, "words_per_scene": 10, "style": "punchy and fast-paced", "hook_words": 8},
        30: {"total_words": 70, "words_per_scene": 12, "style": "engaging but brisk", "hook_words": 10},
        60: {"total_words": 140, "words_per_scene": 15, "style": "detailed yet conversational", "hook_words": 12},
    }
    config = duration_config.get(duration_seconds, duration_config[30])

    # Tone-specific guidance
    tone_guidance = {
        "luxury": "sophisticated, exclusive, aspirational language. Use words like 'stunning', 'exquisite', 'exceptional'",
        "cozy": "warm, inviting, comfortable language. Use words like 'charming', 'welcoming', 'perfect for'",
        "modern": "clean, contemporary, fresh language. Use words like 'sleek', 'updated', 'move-in ready'",
        "minimal": "simple, understated, elegant language. Focus on space and light",
        "bold": "confident, exciting, attention-grabbing language. Use words like 'incredible', 'must-see', 'wow'",
    }

    # Format price nicely (must be before system_prompt which uses it)
    price = listing_data.get('price', 0) or 0
    if price >= 1000000:
        price_str = f"${price/1000000:.1f}M".replace('.0M', 'M')
    elif price > 0:
        price_str = f"${price/1000:,.0f}K"
    else:
        price_str = "this price"

    system_prompt = f"""<BANNED_PHRASES>
NEVER use these phrases - they will cause immediate rejection:
- "Welcome to" (BANNED - never start any sentence with this)
- "Step inside"
- "This stunning property"
- "This beautiful home"
- "Featuring"
- "Boasts"
- "Nestled"
- "Situated"
- Any phrase that sounds like a real estate listing or brochure
</BANNED_PHRASES>

You write TikTok/Instagram Reels voiceovers that sound like a 25-year-old influencer FaceTiming their friend about a house they just toured. NOT a real estate agent. NOT a brochure.

<WRONG_EXAMPLE>
"Welcome to this stunning 4-bedroom home in Kingston. This beautiful property features an updated kitchen and spacious living areas."
</WRONG_EXAMPLE>

<CORRECT_EXAMPLE>
"Okay wait... {price_str} for THIS in Kingston?? Four beds, the kitchen is literally insane, and don't even get me started on the backyard."
</CORRECT_EXAMPLE>

STYLE: {config['style']} | ~{config['total_words']} total words | ~{config['words_per_scene']} per scene

TONE: {tone_guidance.get(tone, tone_guidance['modern'])}

Start with ONE of these hook styles:
- "POV: you just found..."
- "Okay but [price] for THIS??"
- "Wait till you see..."
- "This might be the one..."
- "Stop scrolling if you're looking in [area]"

Output ONLY raw JSON. No markdown."""

    # Format square feet
    sqft = listing_data.get('square_feet', 0)
    sqft_str = f"{sqft:,}" if sqft else "spacious"

    user_prompt = f"""Listing:
📍 {listing_data.get('address', 'Amazing Property')}
💰 {price_str} | 🛏️ {listing_data.get('bedrooms', '?')}bd/{listing_data.get('bathrooms', '?')}ba | 📐 {sqft_str}sqft
📌 {listing_data.get('neighborhood', listing_data.get('city', ''))}
✨ {', '.join(listing_data.get('features', [])[:3]) or 'great layout'}

Write {scene_count} scenes for a {duration_seconds}s video. Return JSON:
{{
    "hook": "POV: you just found your dream home in {listing_data.get('neighborhood', listing_data.get('city', 'the city'))}",
    "scenes": [
        {{"scene_number": 1, "narration": "Okay {price_str} for this?? Let me show you around..."}},
        {{"scene_number": 2, "narration": "The kitchen is giving everything it needs to give..."}},
        {{"scene_number": 3, "narration": "And don't even get me started on this view..."}}
    ],
    "cta": "Save this and DM me if you want more details",
    "caption": "Found this gem in [area] and I'm obsessed. {price_str} for [X]beds - thoughts?? 👀",
    "hashtags": ["realestate", "{listing_data.get('city', 'home').lower().replace(' ', '')}", "housetour", "dreamhome", "fyp"]
}}

IMPORTANT: The example narrations above show the EXACT casual tone I need. Write similar vibes but for THIS specific property. Never use "Welcome to" or formal language."""

    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt},
        ],
    )

    response_text = response.content[0].text
    logger.debug(f"Raw Anthropic response: {response_text[:500]}")

    # Try to parse as-is first
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code blocks
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find JSON object in the response
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # If all else fails, raise with context
    raise ValueError(f"Could not parse JSON from Anthropic response: {response_text[:200]}")


def generate_voiceover_sync(text: str, voice_settings: dict) -> dict:
    """Generate voiceover using ElevenLabs."""
    import httpx

    voice_id = voice_settings.get("voice_id") or "21m00Tcm4TlvDq8ikWAM"  # Rachel default

    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers=headers,
            json=payload,
        )

        if response.status_code != 200:
            raise Exception(f"ElevenLabs API error: {response.text}")

        audio_data = response.content

        # Estimate duration
        word_count = len(text.split())
        duration_seconds = word_count / 2.5

        return {
            "audio_data": audio_data,
            "duration_seconds": duration_seconds,
        }


# Global HTTP client for reuse (connection pooling)
_http_client = None

def get_http_client() -> httpx.Client:
    """Get a reusable HTTP client with connection pooling."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(timeout=60.0, limits=httpx.Limits(max_connections=10))
    return _http_client


def ensure_minimum_image_size(image_url: str, min_size: int = 300) -> str:
    """Download image, upscale if needed, and return a data URL or the original URL."""
    from PIL import Image
    import base64

    # Skip processing for data URLs (already processed)
    if image_url.startswith("data:"):
        return image_url

    try:
        client = get_http_client()
        response = client.get(image_url)
        if response.status_code != 200:
            logger.warning(f"Failed to fetch image: {response.status_code}")
            return image_url

        img = Image.open(io.BytesIO(response.content))
        width, height = img.size

        # Check if upscaling is needed - most images won't need it
        if width >= min_size and height >= min_size:
            return image_url

        # Calculate new size maintaining aspect ratio
        scale = max(min_size / width, min_size / height)
        new_width = int(width * scale)
        new_height = int(height * scale)

        logger.debug(f"Upscaling image from {width}x{height} to {new_width}x{new_height}")
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convert to RGB if needed (for JPEG)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # Save to bytes and create data URL
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)  # Slightly lower quality for speed
        img_bytes = buffer.getvalue()

        # Return as data URL
        b64_data = base64.b64encode(img_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{b64_data}"
    except Exception as e:
        logger.warning(f"Image processing error: {e}")
        return image_url


def generate_scene_clip_sync(
    image_url: str,
    narration: str,
    camera_movement: dict,
    duration_ms: int,
    style_settings: dict,
) -> dict:
    """Generate a video clip for a scene using fal.ai."""
    import fal_client
    import os

    os.environ["FAL_KEY"] = settings.FAL_KEY

    # Ensure image meets minimum size requirements
    image_url = ensure_minimum_image_size(image_url, min_size=300)

    motion_type = camera_movement.get("type", "zoom_in")
    tone = style_settings.get("tone", "modern")
    video_model = style_settings.get("video_model", "kling")

    # Model mapping - user-friendly names to fal.ai model IDs
    MODEL_MAP = {
        "kling": "fal-ai/kling-video/v1/standard/image-to-video",
        "kling_pro": "fal-ai/kling-video/v1/pro/image-to-video",
        "kling_v2": "fal-ai/kling-video/v2.6/pro/image-to-video",
        "veo3": "fal-ai/veo3.1/image-to-video",
        "veo3_fast": "fal-ai/veo3.1/fast/image-to-video",
        "minimax": "fal-ai/minimax/video-01/image-to-video",
        "runway": "fal-ai/runway-gen3/turbo/image-to-video",
    }
    model_id = MODEL_MAP.get(video_model, MODEL_MAP["kling"])

    # Build cinematic prompt with professional filmmaking terminology
    tone_cinematics = {
        "luxury": {
            "look": "luxury real estate commercial, Architectural Digest aesthetic",
            "lighting": "golden hour warm sunlight streaming through windows, soft shadows",
            "mood": "aspirational, sophisticated, exclusive",
            "color": "warm color grading, rich earth tones, subtle gold highlights",
        },
        "cozy": {
            "look": "lifestyle home video, HGTV aesthetic",
            "lighting": "soft diffused natural light, warm ambient glow",
            "mood": "inviting, comfortable, lived-in feel",
            "color": "warm muted tones, soft contrast, homey atmosphere",
        },
        "modern": {
            "look": "sleek real estate commercial, contemporary design showcase",
            "lighting": "bright natural daylight, clean shadows, high key lighting",
            "mood": "fresh, clean, move-in ready",
            "color": "neutral color palette, crisp whites, subtle blues",
        },
        "minimal": {
            "look": "minimalist architecture video, Kinfolk magazine aesthetic",
            "lighting": "soft natural light, gentle shadows, zen-like atmosphere",
            "mood": "serene, peaceful, uncluttered",
            "color": "desaturated, monochromatic, subtle earth tones",
        },
        "bold": {
            "look": "dramatic real estate showcase, high-end production value",
            "lighting": "dramatic contrast, strong directional light, cinematic shadows",
            "mood": "impressive, striking, memorable",
            "color": "high contrast, saturated colors, film-like color grading",
        },
    }

    style = tone_cinematics.get(tone, tone_cinematics["modern"])

    # Camera movement descriptions for more cinematic results
    camera_descriptions = {
        "zoom_in": "slow smooth dolly push-in, gradually revealing details, steadicam movement",
        "zoom_out": "elegant pull-back shot revealing the full space, smooth dolly out",
        "pan_left": "cinematic lateral tracking shot moving left, gimbal-stabilized",
        "pan_right": "cinematic lateral tracking shot moving right, gimbal-stabilized",
        "pan_up": "smooth tilt up revealing height and grandeur, crane-like movement",
        "pan_down": "gentle tilt down in welcoming motion, descending reveal",
        "orbit_left": "elegant orbit shot rotating left around the space, 360 feel",
        "orbit_right": "elegant orbit shot rotating right around the space, 360 feel",
        "static": "subtle parallax movement, gentle floating camera, ambient motion",
    }
    camera_desc = camera_descriptions.get(motion_type, camera_descriptions["zoom_in"])

    prompt = f"""{style['look']}, {camera_desc},
{style['lighting']}, {style['mood']}, {style['color']},
professional real estate cinematography, shot on RED camera,
shallow depth of field, smooth 24fps motion,
no text overlays, no watermarks, photorealistic, 4K ultra HD quality"""

    # Negative prompt to avoid common issues
    negative_prompt = """shaky camera, jerky motion, fast movement, blurry, distorted,
text, watermark, logo, low quality, amateur, handheld shake,
overexposed, underexposed, grainy, noisy, artifacts,
unnatural motion, morphing, warping, glitches"""

    # Build model-specific arguments
    if video_model in ["kling", "kling_pro", "kling_v2"]:
        arguments = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "image_url": image_url,
            "duration": "5",
            "aspect_ratio": "9:16",
        }
    elif video_model in ["veo3", "veo3_fast"]:
        arguments = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "image_url": image_url,
            "aspect_ratio": "9:16",
            "duration": "5s",
        }
    elif video_model == "minimax":
        arguments = {
            "prompt": prompt,
            "image_url": image_url,
        }
    elif video_model == "runway":
        arguments = {
            "prompt": prompt,
            "image_url": image_url,
            "duration": 5,
            "ratio": "9:16",
        }
    else:
        arguments = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "image_url": image_url,
            "duration": "5",
            "aspect_ratio": "9:16",
        }

    logger.debug(f"Using video model: {model_id}")
    logger.debug(f"Cinematic prompt: {prompt[:200]}...")
    handler = fal_client.submit(model_id, arguments=arguments)
    result = handler.get()

    return {
        "video_url": result["video"]["url"],
        "width": result.get("video", {}).get("width", 1080),
        "height": result.get("video", {}).get("height", 1920),
    }


def composite_video_sync(
    video_clips: list[dict],
    voiceover_data: bytes | None,
    style_settings: dict,
) -> str:
    """Composite video clips with audio using FFmpeg."""
    import subprocess
    import tempfile

    temp_dir = tempfile.mkdtemp()

    try:
        # Download all video clips IN PARALLEL
        clip_paths = [None] * len(video_clips)

        def download_clip(idx: int, clip: dict) -> tuple[int, str]:
            clip_path = os.path.join(temp_dir, f"clip_{idx}.mp4")
            with httpx.Client(timeout=60.0) as client:
                response = client.get(clip["video_url"])
                with open(clip_path, "wb") as f:
                    f.write(response.content)
            return idx, clip_path

        with ThreadPoolExecutor(max_workers=len(video_clips)) as executor:
            futures = [executor.submit(download_clip, i, clip) for i, clip in enumerate(video_clips)]
            for future in futures:
                idx, path = future.result()
                clip_paths[idx] = path

        # Create concat file
        concat_file = os.path.join(temp_dir, "concat.txt")
        with open(concat_file, "w") as f:
            for path in clip_paths:
                f.write(f"file '{path}'\n")

        # Concatenate videos
        concat_output = os.path.join(temp_dir, "concat.mp4")
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file, "-c", "copy", concat_output
            ],
            check=True,
            capture_output=True,
        )

        # Add voiceover if available
        final_output = os.path.join(temp_dir, "final.mp4")

        if voiceover_data:
            audio_path = os.path.join(temp_dir, "voiceover.mp3")
            with open(audio_path, "wb") as f:
                f.write(voiceover_data)

            # Mix video with voiceover
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", concat_output,
                    "-i", audio_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-shortest",
                    final_output
                ],
                check=True,
                capture_output=True,
            )
        else:
            # Just copy the concatenated video
            subprocess.run(
                ["cp", concat_output, final_output],
                check=True,
            )

        return final_output

    except subprocess.CalledProcessError as e:
        raise Exception(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")


def upload_to_storage(file_path: str, project_id: str) -> tuple[str, int]:
    """Upload video to Supabase Storage and return URL."""
    from supabase import create_client

    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY)

    timestamp = datetime.utcnow().strftime("%Y/%m/%d")
    storage_key = f"videos/{project_id}/{timestamp}/tour_video.mp4"

    file_size = os.path.getsize(file_path)

    with open(file_path, "rb") as f:
        file_data = f.read()

    # Upload to Supabase Storage bucket "generated-content"
    result = supabase.storage.from_("generated-content").upload(
        storage_key,
        file_data,
        file_options={"content-type": "video/mp4"}
    )

    # Get public URL
    url_result = supabase.storage.from_("generated-content").get_public_url(storage_key)
    output_url = url_result

    return output_url, file_size


def update_scenes_with_script(db: Session, project_id: str, scenes: list[dict]):
    """Update scene records with generated narration."""
    from app.models.project import Scene

    db_scenes = db.query(Scene).filter(Scene.project_id == project_id).order_by(Scene.sequence_order).all()

    for i, db_scene in enumerate(db_scenes):
        if i < len(scenes):
            db_scene.narration_text = scenes[i].get("narration", "")

    db.commit()


def update_project_content(db: Session, project_id: str, script: dict, caption: str, hashtags: list[str]):
    """Update project with generated content."""
    from app.models.project import Project

    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        project.generated_script = script
        project.generated_caption = caption
        project.generated_hashtags = hashtags
        project.status = "completed"
        db.commit()


@celery_app.task(
    bind=True,
    name="regenerate_scene",
    max_retries=2,
)
def regenerate_scene_task(
    self,
    project_id: str,
    scene_id: str,
    image_url: str,
    camera_movement: dict,
    duration_ms: int,
    style_settings: dict,
) -> dict:
    """Regenerate a single scene's video."""
    try:
        result = generate_scene_clip_sync(
            image_url=image_url,
            narration="",
            camera_movement=camera_movement,
            duration_ms=duration_ms,
            style_settings=style_settings,
        )

        return {
            "status": "completed",
            "scene_id": scene_id,
            "video_url": result["video_url"],
        }

    except Exception as e:
        return {
            "status": "failed",
            "scene_id": scene_id,
            "error": str(e),
        }
