"""Script generation service using Anthropic Claude."""

import json
from typing import Any

import anthropic
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.brand_kit import BrandKit
from app.models.media import MediaAsset
from app.models.project import Project, Scene
from app.models.property import PropertyListing
from app.services.circuit_breaker import get_circuit_breaker, CircuitBreakerOpen
from app.services.sanitization import sanitize_text


def _sanitize_for_prompt(text: str | None, max_length: int = 500) -> str:
    """
    Sanitize user-provided text before including in AI prompts.
    Prevents prompt injection attacks.
    """
    if not text:
        return ""
    return sanitize_text(text, max_length=max_length, allow_newlines=False)


class ScriptScene(BaseModel):
    """Generated scene data."""
    scene_number: int
    duration_seconds: int
    narration: str
    on_screen_text: str
    suggested_photo_index: int
    emotion: str


class GeneratedScript(BaseModel):
    """Complete generated script."""
    hook: str
    scenes: list[ScriptScene]
    cta: str
    estimated_word_count: int


# Circuit breaker for Anthropic API
anthropic_breaker = get_circuit_breaker("anthropic", failure_threshold=5, recovery_timeout=60)


class ScriptGeneratorService:
    """Service for generating video scripts using Anthropic Claude."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.ANTHROPIC_MODEL

    async def _call_anthropic(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.8,
    ) -> str:
        """
        Call Anthropic API with circuit breaker protection.

        Returns the text content from Claude's response.
        """
        async def make_request():
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
            )
            return response.content[0].text

        return await anthropic_breaker.call(make_request)

    async def generate_script(
        self,
        project: Project,
        db: AsyncSession,
        regenerate: bool = False,
    ) -> GeneratedScript:
        """Generate a complete video script for a project."""

        # Get related data
        property_listing = None
        if project.property_id:
            result = await db.execute(
                select(PropertyListing).where(PropertyListing.id == project.property_id)
            )
            property_listing = result.scalar_one_or_none()

        brand_kit = None
        if project.brand_kit_id:
            result = await db.execute(
                select(BrandKit).where(BrandKit.id == project.brand_kit_id)
            )
            brand_kit = result.scalar_one_or_none()

        # Get uploaded photos
        result = await db.execute(
            select(MediaAsset)
            .where(MediaAsset.project_id == project.id, MediaAsset.file_type == "image")
            .order_by(MediaAsset.created_at)
        )
        photos = result.scalars().all()

        # Build prompt
        style = project.style_settings
        duration = style.get("duration_seconds", 30)
        scene_count = self._calculate_scene_count(duration)

        system_prompt = self._get_system_prompt()
        user_prompt = self._build_user_prompt(
            project=project,
            property_listing=property_listing,
            brand_kit=brand_kit,
            photos=photos,
            duration=duration,
            scene_count=scene_count,
        )

        # Call Anthropic Claude
        content = await self._call_anthropic(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=2000,
            temperature=0.8,
        )

        # Parse JSON response (Claude may wrap in markdown code blocks)
        json_content = self._extract_json(content)
        data = json.loads(json_content)

        return GeneratedScript(
            hook=data["hook"],
            scenes=[ScriptScene(**s) for s in data["scenes"]],
            cta=data["cta"],
            estimated_word_count=data.get("estimated_word_count", 0),
        )

    async def regenerate_scene(
        self,
        scene: Scene,
        all_scenes: list[Scene],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Regenerate text for a specific scene."""

        # Find adjacent scenes
        prev_scene = None
        next_scene = None
        for i, s in enumerate(all_scenes):
            if s.id == scene.id:
                if i > 0:
                    prev_scene = all_scenes[i - 1]
                if i < len(all_scenes) - 1:
                    next_scene = all_scenes[i + 1]
                break

        prompt = f"""
Rewrite ONLY this specific scene from a real estate video script.

## Context
Previous scene narration: "{prev_scene.narration_text if prev_scene else 'None - this is the first scene'}"
Current scene (to rewrite): "{scene.narration_text}"
Next scene narration: "{next_scene.narration_text if next_scene else 'None - this is the last scene'}"

## Requirements
- Keep the same approximate duration ({scene.duration_ms // 1000} seconds)
- Maintain flow with surrounding scenes
- Highlight different aspects or use different phrasing
- On-screen text must be under 40 characters for mobile readability

Respond with JSON only (no markdown code blocks):
{{
    "narration": "New voiceover text",
    "on_screen_text": "NEW TEXT",
    "emotion": "the emotional tone"
}}
"""

        content = await self._call_anthropic(
            system_prompt="You are a real estate copywriter. Respond with valid JSON only.",
            user_prompt=prompt,
            max_tokens=500,
            temperature=0.9,
        )

        json_content = self._extract_json(content)
        return json.loads(json_content)

    async def generate_caption(
        self,
        project: Project,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Generate social media caption and hashtags."""

        # Get property details
        property_listing = None
        if project.property_id:
            result = await db.execute(
                select(PropertyListing).where(PropertyListing.id == project.property_id)
            )
            property_listing = result.scalar_one_or_none()

        property_info = ""
        if property_listing:
            # Sanitize user-provided fields to prevent prompt injection
            safe_address = _sanitize_for_prompt(property_listing.full_address, 200)
            safe_status = _sanitize_for_prompt(
                property_listing.listing_status.replace("_", " ").title() if property_listing.listing_status else "",
                50
            )
            safe_features = ", ".join([
                _sanitize_for_prompt(f, 100) for f in (property_listing.features or [])[:20]
            ])

            property_info = f"""
Address: {safe_address}
Price: ${property_listing.listing_price:,.0f}
{property_listing.bedrooms} bed / {property_listing.bathrooms} bath | {property_listing.square_feet:,} sq ft
Status: {safe_status}
Features: {safe_features}
"""

        prompt = f"""
Write a social media caption for a real estate listing video.

## Property
{property_info or 'Property details not provided'}

## Platform
{project.style_settings.get('platform', 'Instagram Reels')}

## Requirements
- Start with a hook (emoji optional)
- Keep under 200 characters for optimal engagement
- Include soft CTA (not pushy)
- Suggest 5-8 relevant hashtags
- Optionally suggest a "first comment" with additional hashtags

Respond with JSON only (no markdown code blocks):
{{
    "caption": "The main caption text",
    "hashtags": ["#JustListed", "#RealEstate", ...],
    "first_comment": "Optional additional hashtags or engagement prompt"
}}
"""

        content = await self._call_anthropic(
            system_prompt="You are a social media marketing expert for real estate. Respond with valid JSON only.",
            user_prompt=prompt,
            max_tokens=500,
            temperature=0.7,
        )

        json_content = self._extract_json(content)
        return json.loads(json_content)

    async def generate_shot_plan(
        self,
        project: Project,
        scenes: list[Scene],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Generate camera movements for all scenes."""

        pace = project.style_settings.get("pace", "moderate")
        pace_descriptions = {
            "calm": "Slow, deliberate movements for a luxury feel",
            "moderate": "Balanced pacing, professional and engaging",
            "fast": "Quick, energetic movements for TikTok-style content",
        }

        scenes_text = "\n".join([
            f"Scene {s.sequence_order}: {s.narration_text[:100]}..."
            for s in scenes
        ])

        prompt = f"""
Create a shot plan for a {len(scenes)}-scene real estate video.

## Pace Setting
{pace} ({pace_descriptions.get(pace, 'Balanced pacing')})

## Scenes
{scenes_text}

## Available Movements
- zoom_in: Push into the image (creates intimacy, reveals detail)
- zoom_out: Pull back from image (reveals scope, establishes space)
- pan_left: Horizontal slide left
- pan_right: Horizontal slide right
- pan_up: Vertical slide up (reveals height, grandeur)
- pan_down: Vertical slide down (welcoming, grounding)

## Requirements
- First and last scenes should have more impactful movements
- Avoid repeating the same movement type consecutively
- Match transition style to the pace setting

Respond with JSON only (no markdown code blocks):
{{
    "scenes": [
        {{
            "scene_number": 1,
            "movement": {{
                "type": "zoom_in",
                "start_position": {{"x": 0.5, "y": 0.5, "scale": 1.0}},
                "end_position": {{"x": 0.55, "y": 0.45, "scale": 1.15}},
                "easing": "ease-in-out"
            }},
            "transition_to_next": {{
                "type": "crossfade",
                "duration_ms": 500
            }}
        }}
    ]
}}
"""

        content = await self._call_anthropic(
            system_prompt="You are a cinematographer planning camera movements for real estate videos. Respond with valid JSON only.",
            user_prompt=prompt,
            max_tokens=2000,
            temperature=0.6,
        )

        json_content = self._extract_json(content)
        return json.loads(json_content)

    def _extract_json(self, content: str) -> str:
        """Extract JSON from content that may be wrapped in markdown code blocks."""
        content = content.strip()

        # Handle markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        return content.strip()

    def _calculate_scene_count(self, duration_seconds: int) -> int:
        """Calculate optimal scene count based on duration."""
        if duration_seconds <= 15:
            return 4
        elif duration_seconds <= 30:
            return 6
        elif duration_seconds <= 45:
            return 8
        else:
            return 10

    def _get_system_prompt(self) -> str:
        """Get the system prompt for script generation."""
        return """You are an expert real estate copywriter who creates compelling video scripts for property listings. Your scripts are designed for short-form vertical video (Instagram Reels, TikTok) and must:

1. Hook viewers in the first 3 seconds
2. Highlight key property features naturally
3. Create emotional connection with the target audience
4. Include a clear call-to-action
5. Stay within strict time limits

IMPORTANT RULES:
- Never invent property details not provided
- Never use discriminatory language or target/exclude protected classes
- Never make promises about property value, appreciation, or investment returns
- Use professional, compliant real estate language
- Keep on-screen text under 40 characters for mobile readability
- Use "primary bedroom" instead of "master bedroom"

Output format: Valid JSON only (no markdown code blocks)"""

    def _build_user_prompt(
        self,
        project: Project,
        property_listing: PropertyListing | None,
        brand_kit: BrandKit | None,
        photos: list[MediaAsset],
        duration: int,
        scene_count: int,
    ) -> str:
        """Build the user prompt for script generation.

        SECURITY: All user-provided text is sanitized to prevent prompt injection.
        """

        property_info = "Property details not provided"
        if property_listing:
            # Sanitize all user-provided fields to prevent prompt injection
            safe_address = _sanitize_for_prompt(property_listing.full_address, 200)
            safe_neighborhood = _sanitize_for_prompt(property_listing.neighborhood, 100) or "the area"
            safe_status = _sanitize_for_prompt(
                property_listing.listing_status.replace("_", " ").title() if property_listing.listing_status else "",
                50
            )
            safe_features = ", ".join([
                _sanitize_for_prompt(f, 100) for f in (property_listing.features or [])[:20]
            ])
            safe_target = _sanitize_for_prompt(property_listing.target_audience, 100) or "home buyers"

            property_info = f"""
Address: {safe_address}
Neighborhood: {safe_neighborhood}
Price: ${property_listing.listing_price:,.0f}
Bedrooms: {property_listing.bedrooms}
Bathrooms: {property_listing.bathrooms}
Square Feet: {property_listing.square_feet:,}
Status: {safe_status}
Key Features: {safe_features}
Target Audience: {safe_target}
"""

        agent_info = "Agent info not provided"
        if brand_kit:
            # Sanitize agent info to prevent prompt injection
            safe_agent_name = _sanitize_for_prompt(brand_kit.agent_name, 100) or "Agent"
            safe_brokerage = _sanitize_for_prompt(brand_kit.brokerage_name, 100) or ""
            safe_phone = _sanitize_for_prompt(brand_kit.agent_phone, 30) or ""

            agent_info = f"""
Agent: {safe_agent_name}
Brokerage: {safe_brokerage}
Phone: {safe_phone}
"""

        style = project.style_settings
        photo_descriptions = "\n".join([
            f"Photo {i+1}: {p.category or 'unknown'} - {p.ai_description or 'No description'}"
            for i, p in enumerate(photos[:12])
        ]) or "No photos uploaded yet"

        return f"""
Create a {duration}-second video script for this property listing.

## Property Information
{property_info}

## Style Parameters
Tone: {style.get('tone', 'modern')}
Pace: {style.get('pace', 'moderate')}
Platform: {style.get('platform', 'instagram_reels')}

## Available Photos
{photo_descriptions}

## Agent Information
{agent_info}

---

Generate a script with {scene_count} scenes. Each scene should be approximately {duration // scene_count} seconds.

Respond with JSON only (no markdown code blocks):
{{
    "hook": "The attention-grabbing first line",
    "scenes": [
        {{
            "scene_number": 1,
            "duration_seconds": 5,
            "narration": "The voiceover text for this scene",
            "on_screen_text": "SHORT TEXT",
            "suggested_photo_index": 0,
            "emotion": "excitement"
        }}
    ],
    "cta": "The final call to action",
    "estimated_word_count": 75
}}
"""
