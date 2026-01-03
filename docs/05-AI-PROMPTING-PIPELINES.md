# ReelEstate Studio - AI Prompting & Pipelines

## 1. AI Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI PIPELINE ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │   User Input    │
                              │  (Photos, Info) │
                              └────────┬────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           STAGE 1: ANALYSIS                                   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │  Photo Analysis │    │ Property Parser │    │  Brand Context  │          │
│  │  (GPT-4 Vision) │    │     (LLM)       │    │   (Database)    │          │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘          │
│           └──────────────────────┴──────────────────────┘                    │
│                                  │                                           │
└──────────────────────────────────┼───────────────────────────────────────────┘
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        STAGE 2: CONTENT GENERATION                            │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │ Script Generator│    │  Shot Planner   │    │ Caption Writer  │          │
│  │     (LLM)       │    │     (LLM)       │    │     (LLM)       │          │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘          │
│           └──────────────────────┴──────────────────────┘                    │
│                                  │                                           │
└──────────────────────────────────┼───────────────────────────────────────────┘
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                      STAGE 3: AI VIDEO GENERATION (fal.ai)                    │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │ fal.ai Kling    │    │ fal.ai Luma     │    │ fal.ai Runway   │          │
│  │ (Image→Video)   │    │ (Dream Machine) │    │ (Gen-3 Turbo)   │          │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘          │
│           └──────────────────────┴──────────────────────┘                    │
│                                  │                                           │
└──────────────────────────────────┼───────────────────────────────────────────┘
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         STAGE 4: MEDIA GENERATION                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │ Voice Generator │    │ Avatar Generator│    │ Layout Generator│          │
│  │  (ElevenLabs)   │    │    (HeyGen)     │    │     (LLM)       │          │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘          │
│           └──────────────────────┴──────────────────────┘                    │
│                                  │                                           │
└──────────────────────────────────┼───────────────────────────────────────────┘
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          STAGE 5: COMPOSITION                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │ Video Compositor│    │ Audio Mixer     │    │ Graphics Render │          │
│  │   (FFmpeg)      │    │   (FFmpeg)      │    │   (Pillow)      │          │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘          │
│           └──────────────────────┴──────────────────────┘                    │
│                                  │                                           │
└──────────────────────────────────┼───────────────────────────────────────────┘
                                   ▼
                              ┌─────────────────┐
                              │  Final Output   │
                              │  (MP4 / PNG)    │
                              └─────────────────┘
```

---

## 1.1 fal.ai Video Generation Pipeline

The platform uses **fal.ai** for AI-powered video generation, transforming static property photos into cinematic video clips with realistic motion.

### Available Models

| Model | Best For | Duration | Quality |
|-------|----------|----------|---------|
| **Kling Standard** | Primary property tours | 5-10s | High |
| **Kling Pro** | Luxury listings | 5-10s | Highest |
| **Luma Dream Machine** | Smooth cinematic motion | 5s | High |
| **Runway Gen-3 Turbo** | Fast generation | 5-10s | Good |
| **Fast SVD-LCM** | Quick previews | 2-4s | Medium |
| **MiniMax** | Extended clips | Up to 6s | High |

### Camera Motion Types

```python
class CameraMotion(str, Enum):
    ZOOM_IN = "zoom in"       # Push into image (intimacy, detail)
    ZOOM_OUT = "zoom out"     # Pull back (scope, space)
    PAN_LEFT = "pan left"     # Horizontal slide left
    PAN_RIGHT = "pan right"   # Horizontal slide right
    PAN_UP = "tilt up"        # Reveal height, grandeur
    PAN_DOWN = "tilt down"    # Welcoming, grounding
    STATIC = "static"         # Subtle ambient motion
    ORBIT_LEFT = "orbit left" # Orbit around subject
    ORBIT_RIGHT = "orbit right"
```

### Video Generation Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   Image     │────▶│  fal.ai API  │────▶│  AI Video   │────▶│  S3 Storage  │
│   (S3 URL)  │     │  (Kling/Luma)│     │  (5-10 sec) │     │  (CDN URL)   │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
       │                   │
       │                   ▼
       │            ┌──────────────┐
       └───────────▶│ Motion Prompt│
                    │ (camera dir, │
                    │  tone, style)│
                    └──────────────┘
```

---

## 2. System Prompts & Templates

### 2.1 Photo Analysis Prompt (GPT-4 Vision)

```python
PHOTO_ANALYSIS_SYSTEM_PROMPT = """
You are a real estate photography analyst. Your job is to analyze property photos 
and provide structured information to help create marketing content.

For each image, identify:
1. Room/area type (exterior, kitchen, bathroom, bedroom, living room, etc.)
2. Key features visible (appliances, fixtures, views, architectural details)
3. Quality score (1-10) based on lighting, composition, and marketability
4. Suggested camera movements for video (pan left/right, zoom in/out, static)
5. Best text overlay positions (areas with less visual detail)

Always respond in valid JSON format.
"""

PHOTO_ANALYSIS_USER_PROMPT = """
Analyze this property photo for a real estate marketing video.

Property context:
- Address: {address}
- Price: {price}
- Key selling points: {features}

Respond with:
{{
  "room_type": "string",
  "detected_features": ["feature1", "feature2"],
  "quality_score": 8,
  "suggested_movement": {{
    "type": "zoom_in" | "pan_left" | "pan_right" | "pan_up" | "pan_down" | "static",
    "intensity": "subtle" | "moderate" | "dramatic",
    "reason": "why this movement works"
  }},
  "text_safe_zones": ["bottom_left", "top_right"],
  "mood": "luxurious" | "cozy" | "modern" | "traditional" | "minimalist",
  "hero_potential": true | false
}}
"""
```

### 2.2 Script Generation Prompt

```python
SCRIPT_GENERATION_SYSTEM_PROMPT = """
You are an expert real estate copywriter who creates compelling video scripts for 
property listings. Your scripts are designed for short-form vertical video (Instagram 
Reels, TikTok) and must:

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

Output format: JSON with scene-by-scene breakdown
"""

SCRIPT_GENERATION_USER_PROMPT = """
Create a {duration}-second video script for this property listing.

## Property Information
Address: {address}
Neighborhood: {neighborhood}
Price: ${price:,}
Bedrooms: {bedrooms}
Bathrooms: {bathrooms}
Square Feet: {square_feet:,}
Status: {status}
Key Features: {features}

## Target Audience
{target_audience}

## Style Parameters
Tone: {tone}
Pace: {pace}
Platform: {platform}

## Available Photos (in order of quality)
{photo_descriptions}

## Agent Information
Agent: {agent_name}
Brokerage: {brokerage}
Phone: {phone}

---

Generate a script with {scene_count} scenes. Each scene should be approximately 
{seconds_per_scene} seconds.

Respond in this exact JSON format:
{{
  "hook": "The attention-grabbing first line",
  "scenes": [
    {{
      "scene_number": 1,
      "duration_seconds": 5,
      "narration": "The voiceover text for this scene",
      "on_screen_text": "SHORT TEXT",
      "suggested_photo_index": 0,
      "emotion": "excitement" | "warmth" | "aspiration" | "urgency"
    }}
  ],
  "cta": "The final call to action",
  "estimated_word_count": 75
}}
"""
```

### 2.3 Scene Regeneration Prompt

```python
SCENE_REGENERATION_PROMPT = """
Rewrite ONLY this specific scene from a real estate video script.

## Context
Property: {address} - ${price:,}
Target audience: {target_audience}
Overall tone: {tone}

## Current Script Flow
Previous scene: "{previous_narration}"
Current scene (to rewrite): "{current_narration}"
Next scene: "{next_narration}"

## Photo Being Used
{photo_description}

## Requirements
- Keep the same approximate duration ({duration} seconds)
- Maintain flow with surrounding scenes
- Highlight different aspects or use different phrasing
- On-screen text must be under 40 characters

Respond with:
{{
  "narration": "New voiceover text",
  "on_screen_text": "NEW TEXT",
  "emotion": "the emotional tone"
}}
"""
```

### 2.4 Shot Planning Prompt

```python
SHOT_PLANNING_SYSTEM_PROMPT = """
You are a cinematographer planning camera movements for a real estate video 
made from still photographs. Your job is to:

1. Create natural, flowing camera movements using Ken Burns effect
2. Guide the viewer's eye to important features
3. Maintain visual variety (don't repeat the same movement twice in a row)
4. Match movement intensity to the video's pace setting
5. Consider safe zones for text overlays

Movement types available:
- zoom_in: Push into the image (creates intimacy, reveals detail)
- zoom_out: Pull back from image (reveals scope, establishes space)
- pan_left: Horizontal slide left (natural reading direction feel)
- pan_right: Horizontal slide right (progressive reveal)
- pan_up: Vertical slide up (reveals height, grandeur)
- pan_down: Vertical slide down (welcoming, grounding)
- ken_burns: Diagonal movement combining pan and zoom

Transition types:
- crossfade: Smooth dissolve (default, elegant)
- cut: Hard cut (energetic, modern)
- slide_left: Current image slides left, new slides in from right
- slide_right: Opposite of slide_left
- zoom_through: Zoom into current, zoom out of next (dramatic)
- whip_pan: Fast blur transition (very energetic)
"""

SHOT_PLANNING_USER_PROMPT = """
Create a shot plan for a {duration}-second real estate video.

## Pace Setting
{pace} ({pace_description})

## Scenes
{scenes_with_photos}

## Requirements
- First and last scenes should have more impactful movements
- Avoid repeating the same movement type consecutively
- Match transition style to the pace setting
- Consider the room type when choosing movements (wide shots = zoom out, detail shots = zoom in)

Respond with:
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
```

### 2.5 Caption & Hashtag Generation Prompt

```python
CAPTION_GENERATION_PROMPT = """
Write a social media caption for a real estate listing video.

## Property
{address}
{bedrooms} bed / {bathrooms} bath | {square_feet:,} sq ft | ${price:,}
Status: {status}
Key features: {features}

## Agent
{agent_name} | {brokerage}

## Platform
{platform}

## Requirements
- Start with a hook (emoji optional)
- Keep under 200 characters for optimal engagement
- Include soft CTA (not pushy)
- Suggest 5-8 relevant hashtags
- Optionally suggest a "first comment" with additional hashtags

Respond with:
{{
  "caption": "The main caption text",
  "hashtags": ["#JustListed", "#RealEstate", ...],
  "first_comment": "Optional additional hashtags or engagement prompt"
}}
"""
```

### 2.6 Infographic Layout Generation Prompt

```python
INFOGRAPHIC_LAYOUT_PROMPT = """
You are a graphic designer creating real estate infographic layouts.

## Property Information
Address: {address}
Price: ${price:,}
Beds: {bedrooms} | Baths: {bathrooms} | Sq Ft: {square_feet:,}
Status: {status}
Features: {features}
Open House: {open_house_info}

## Brand Kit
Primary Color: {primary_color}
Secondary Color: {secondary_color}
Accent Color: {accent_color}
Heading Font: {heading_font}
Body Font: {body_font}

## Layout Type
{layout_type} ({layout_description})

## Emphasis
{emphasis} - Focus on: {emphasis_description}

## Requirements
- Design for 1080x1920 vertical format
- Ensure text is readable on mobile (min 48px for body, 72px for headings)
- Leave safe zones at top (150px) and bottom (200px) for Instagram UI
- Use brand colors consistently
- Include agent info and logo in footer area

Generate 3 layout variations:

{{
  "layouts": [
    {{
      "id": 1,
      "name": "Clean Modern",
      "description": "Minimalist layout with large hero image",
      "elements": [
        {{
          "type": "image",
          "source": "hero",
          "position": {{"x": 0, "y": 0, "width": 1080, "height": 900}},
          "style": {{"overlay": "gradient_bottom", "overlay_opacity": 0.4}}
        }},
        {{
          "type": "text",
          "content": "$450,000",
          "position": {{"x": 60, "y": 920}},
          "style": {{"font": "heading", "size": 96, "color": "primary", "weight": "bold"}}
        }},
        {{
          "type": "badge",
          "content": "JUST LISTED",
          "position": {{"x": 60, "y": 180}},
          "style": {{"background": "accent", "text_color": "white", "padding": 16}}
        }}
        // ... more elements
      ]
    }}
  ]
}}
"""
```

---

## 3. AI Model Integration Layer

### 3.1 LLM Service Interface

```python
# backend/app/services/ai/llm_service.py

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel

class LLMConfig(BaseModel):
    model: str = "gpt-4-turbo"
    temperature: float = 0.7
    max_tokens: int = 2000
    response_format: Optional[str] = "json_object"

class LLMService(ABC):
    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        config: LLMConfig = LLMConfig()
    ) -> dict:
        pass
    
    @abstractmethod
    async def analyze_image(
        self,
        image_url: str,
        prompt: str,
        config: LLMConfig = LLMConfig()
    ) -> dict:
        pass


class OpenAILLMService(LLMService):
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        config: LLMConfig = LLMConfig()
    ) -> dict:
        response = await self.client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            response_format={"type": config.response_format} if config.response_format else None
        )
        
        return json.loads(response.choices[0].message.content)
    
    async def analyze_image(
        self,
        image_url: str,
        prompt: str,
        config: LLMConfig = LLMConfig()
    ) -> dict:
        response = await self.client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            max_tokens=config.max_tokens
        )
        
        return json.loads(response.choices[0].message.content)
```

### 3.2 Voice Generation Service

```python
# backend/app/services/ai/voice_service.py

from enum import Enum

class VoiceStyle(str, Enum):
    ENERGETIC = "energetic"
    CALM = "calm"
    AUTHORITATIVE = "authoritative"
    FRIENDLY = "friendly"

class VoiceGender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"

# Voice ID mappings for ElevenLabs
VOICE_MAPPINGS = {
    (VoiceGender.FEMALE, VoiceStyle.FRIENDLY): "EXAVITQu4vr4xnSDxMaL",  # Sarah
    (VoiceGender.FEMALE, VoiceStyle.CALM): "jBpfuIE2acCO8z3wKNLl",      # Nicole
    (VoiceGender.MALE, VoiceStyle.FRIENDLY): "onwK4e9ZLuTAKqWW03F9",    # Daniel
    (VoiceGender.MALE, VoiceStyle.AUTHORITATIVE): "N2lVS1w4EtoT3dr4eOWO", # Marcus
    # ... more mappings
}


class VoiceService:
    def __init__(self, api_key: str):
        self.client = ElevenLabs(api_key=api_key)
    
    async def generate_voiceover(
        self,
        text: str,
        gender: VoiceGender,
        style: VoiceStyle,
        output_path: str
    ) -> str:
        """Generate voiceover audio file."""
        
        voice_id = VOICE_MAPPINGS.get((gender, style), VOICE_MAPPINGS[(VoiceGender.FEMALE, VoiceStyle.FRIENDLY)])
        
        audio = await self.client.generate(
            text=text,
            voice=voice_id,
            model="eleven_multilingual_v2",
            voice_settings={
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.5,
                "use_speaker_boost": True
            }
        )
        
        # Save to file
        with open(output_path, 'wb') as f:
            for chunk in audio:
                f.write(chunk)
        
        return output_path
    
    async def get_audio_duration(self, file_path: str) -> float:
        """Get duration of audio file in seconds."""
        import librosa
        duration = librosa.get_duration(path=file_path)
        return duration
```

### 3.3 Avatar Generation Service

```python
# backend/app/services/ai/avatar_service.py

class AvatarService:
    """Integration with HeyGen or D-ID for talking avatar generation."""
    
    def __init__(self, api_key: str, provider: str = "heygen"):
        self.api_key = api_key
        self.provider = provider
        self.base_url = "https://api.heygen.com/v2" if provider == "heygen" else "https://api.d-id.com"
    
    async def create_avatar_video(
        self,
        headshot_url: str,
        script: str,
        voice_id: str,
        output_settings: dict
    ) -> str:
        """Generate talking head video from headshot and script."""
        
        if self.provider == "heygen":
            return await self._heygen_generate(headshot_url, script, voice_id, output_settings)
        else:
            return await self._did_generate(headshot_url, script, voice_id, output_settings)
    
    async def _heygen_generate(
        self,
        headshot_url: str,
        script: str,
        voice_id: str,
        output_settings: dict
    ) -> str:
        payload = {
            "video_inputs": [{
                "character": {
                    "type": "photo",
                    "photo_url": headshot_url
                },
                "voice": {
                    "type": "text",
                    "input_text": script,
                    "voice_id": voice_id
                }
            }],
            "dimension": {
                "width": output_settings.get("width", 1080),
                "height": output_settings.get("height", 1920)
            }
        }
        
        async with aiohttp.ClientSession() as session:
            # Create video
            async with session.post(
                f"{self.base_url}/video/generate",
                headers={"X-Api-Key": self.api_key},
                json=payload
            ) as resp:
                result = await resp.json()
                video_id = result["data"]["video_id"]
            
            # Poll for completion
            while True:
                async with session.get(
                    f"{self.base_url}/video/{video_id}",
                    headers={"X-Api-Key": self.api_key}
                ) as resp:
                    result = await resp.json()
                    if result["data"]["status"] == "completed":
                        return result["data"]["video_url"]
                    elif result["data"]["status"] == "failed":
                        raise Exception("Avatar generation failed")
                
                await asyncio.sleep(5)
```

---

## 4. Content Generation Pipeline

### 4.1 Full Script Generation Pipeline

```python
# backend/app/services/ai/script_generator.py

class ScriptGenerator:
    def __init__(
        self,
        llm_service: LLMService,
        voice_service: VoiceService
    ):
        self.llm = llm_service
        self.voice = voice_service
    
    async def generate_full_script(
        self,
        project: Project,
        property_listing: PropertyListing,
        brand_kit: BrandKit,
        photos: list[MediaAsset],
        style_settings: StyleSettings
    ) -> GeneratedScript:
        """
        Complete pipeline to generate a video script.
        
        Steps:
        1. Analyze all photos
        2. Generate script based on analysis
        3. Plan camera movements
        4. Validate timing
        """
        
        # Step 1: Analyze photos
        photo_analyses = await self._analyze_photos(photos, property_listing)
        
        # Sort photos by quality and categorize
        sorted_photos = self._sort_and_categorize_photos(photo_analyses)
        
        # Step 2: Generate script
        script = await self._generate_script(
            property_listing=property_listing,
            brand_kit=brand_kit,
            photos=sorted_photos,
            style_settings=style_settings
        )
        
        # Step 3: Plan camera movements
        shot_plan = await self._plan_shots(
            script=script,
            photos=sorted_photos,
            style_settings=style_settings
        )
        
        # Step 4: Validate and adjust timing
        validated_script = await self._validate_timing(
            script=script,
            shot_plan=shot_plan,
            target_duration=style_settings.duration_seconds
        )
        
        # Step 5: Generate caption and hashtags
        caption_data = await self._generate_caption(
            property_listing=property_listing,
            brand_kit=brand_kit,
            style_settings=style_settings
        )
        
        return GeneratedScript(
            hook=validated_script["hook"],
            scenes=validated_script["scenes"],
            cta=validated_script["cta"],
            shot_plan=shot_plan,
            caption=caption_data["caption"],
            hashtags=caption_data["hashtags"],
            first_comment=caption_data.get("first_comment")
        )
    
    async def _analyze_photos(
        self,
        photos: list[MediaAsset],
        property_listing: PropertyListing
    ) -> list[PhotoAnalysis]:
        """Analyze all photos in parallel."""
        
        tasks = [
            self.llm.analyze_image(
                image_url=photo.storage_url,
                prompt=PHOTO_ANALYSIS_USER_PROMPT.format(
                    address=property_listing.full_address,
                    price=property_listing.listing_price,
                    features=", ".join(property_listing.features or [])
                )
            )
            for photo in photos
        ]
        
        results = await asyncio.gather(*tasks)
        
        return [
            PhotoAnalysis(
                media_asset_id=photo.id,
                **result
            )
            for photo, result in zip(photos, results)
        ]
    
    async def _generate_script(
        self,
        property_listing: PropertyListing,
        brand_kit: BrandKit,
        photos: list[PhotoAnalysis],
        style_settings: StyleSettings
    ) -> dict:
        """Generate the video script."""
        
        # Calculate scene count based on duration
        scene_count = self._calculate_scene_count(style_settings.duration_seconds)
        
        photo_descriptions = "\n".join([
            f"Photo {i+1}: {p.room_type} - {', '.join(p.detected_features[:3])} (Quality: {p.quality_score}/10)"
            for i, p in enumerate(photos[:12])  # Limit to top 12
        ])
        
        prompt = SCRIPT_GENERATION_USER_PROMPT.format(
            duration=style_settings.duration_seconds,
            address=property_listing.full_address,
            neighborhood=property_listing.neighborhood or "the area",
            price=property_listing.listing_price,
            bedrooms=property_listing.bedrooms,
            bathrooms=property_listing.bathrooms,
            square_feet=property_listing.square_feet,
            status=property_listing.listing_status.replace("_", " ").title(),
            features=", ".join(property_listing.features or []),
            target_audience=property_listing.target_audience or "home buyers",
            tone=style_settings.tone,
            pace=style_settings.pace,
            platform=style_settings.platform,
            photo_descriptions=photo_descriptions,
            agent_name=brand_kit.agent_name,
            brokerage=brand_kit.brokerage_name,
            phone=brand_kit.agent_phone,
            scene_count=scene_count,
            seconds_per_scene=style_settings.duration_seconds // scene_count
        )
        
        return await self.llm.generate(
            system_prompt=SCRIPT_GENERATION_SYSTEM_PROMPT,
            user_prompt=prompt,
            config=LLMConfig(temperature=0.8)
        )
    
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
```

### 4.2 Video Composition Pipeline

```python
# backend/app/services/video/compositor.py

class VideoCompositor:
    """Composes final video from images, audio, and overlays."""
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg = ffmpeg_path
    
    async def compose_video(
        self,
        scenes: list[Scene],
        voiceover_path: str,
        music_path: str,
        brand_kit: BrandKit,
        output_settings: OutputSettings
    ) -> str:
        """
        Full video composition pipeline.
        
        Steps:
        1. Process each scene with Ken Burns effect
        2. Apply transitions between scenes
        3. Add text overlays
        4. Mix audio (voiceover + music)
        5. Add captions
        6. Export final video
        """
        
        # Step 1: Generate scene clips
        scene_clips = []
        for scene in scenes:
            clip_path = await self._create_scene_clip(
                scene=scene,
                output_settings=output_settings
            )
            scene_clips.append(clip_path)
        
        # Step 2: Concatenate with transitions
        video_path = await self._concat_with_transitions(
            clips=scene_clips,
            scenes=scenes,
            output_settings=output_settings
        )
        
        # Step 3: Add overlays
        video_with_overlays = await self._add_overlays(
            video_path=video_path,
            scenes=scenes,
            brand_kit=brand_kit,
            output_settings=output_settings
        )
        
        # Step 4: Mix audio
        final_video = await self._mix_audio(
            video_path=video_with_overlays,
            voiceover_path=voiceover_path,
            music_path=music_path,
            output_settings=output_settings
        )
        
        # Step 5: Generate subtitles
        if output_settings.include_subtitles:
            subtitle_path = await self._generate_subtitles(
                scenes=scenes,
                output_path=final_video.replace(".mp4", ".srt")
            )
        
        return final_video
    
    async def _create_scene_clip(
        self,
        scene: Scene,
        output_settings: OutputSettings
    ) -> str:
        """Apply Ken Burns effect to a single image."""
        
        movement = scene.camera_movement
        duration = scene.duration_ms / 1000
        
        # Calculate zoom and pan parameters
        start_scale = movement.start_position.scale
        end_scale = movement.end_position.scale
        start_x = movement.start_position.x
        end_x = movement.end_position.x
        start_y = movement.start_position.y
        end_y = movement.end_position.y
        
        # FFmpeg zoompan filter
        filter_str = (
            f"zoompan="
            f"z='if(eq(on,1),{start_scale},{start_scale}+({end_scale}-{start_scale})*on/{duration*25})':"
            f"x='iw/2-(iw/zoom/2)+((iw/zoom)*{start_x})+((({end_x}-{start_x})*on/{duration*25})*iw/zoom)':"
            f"y='ih/2-(ih/zoom/2)+((ih/zoom)*{start_y})+((({end_y}-{start_y})*on/{duration*25})*ih/zoom)':"
            f"d={int(duration*25)}:"
            f"s={output_settings.width}x{output_settings.height}:"
            f"fps=25"
        )
        
        output_path = f"/tmp/scene_{scene.id}.mp4"
        
        cmd = [
            self.ffmpeg,
            "-loop", "1",
            "-i", scene.media_asset.storage_url,
            "-vf", filter_str,
            "-t", str(duration),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        
        await self._run_ffmpeg(cmd)
        return output_path
    
    async def _add_overlays(
        self,
        video_path: str,
        scenes: list[Scene],
        brand_kit: BrandKit,
        output_settings: OutputSettings
    ) -> str:
        """Add text overlays, logo, and other graphics."""
        
        # Build filter complex for all overlays
        filter_parts = []
        
        current_time = 0
        for i, scene in enumerate(scenes):
            if scene.on_screen_text:
                start_time = current_time
                end_time = current_time + scene.duration_ms / 1000
                
                # Text overlay with fade in/out
                filter_parts.append(
                    f"drawtext="
                    f"text='{scene.on_screen_text}':"
                    f"fontfile=/fonts/{brand_kit.heading_font}.ttf:"
                    f"fontsize=72:"
                    f"fontcolor=white:"
                    f"x=(w-text_w)/2:"
                    f"y=h-200:"
                    f"enable='between(t,{start_time},{end_time})':"
                    f"alpha='if(lt(t,{start_time+0.3}),(t-{start_time})/0.3,"
                    f"if(gt(t,{end_time-0.3}),({end_time}-t)/0.3,1))'"
                )
            
            current_time += scene.duration_ms / 1000
        
        # Add logo watermark
        if brand_kit.logo_url:
            filter_parts.append(
                f"movie={brand_kit.logo_url}[logo];"
                f"[0:v][logo]overlay=W-w-40:H-h-40"
            )
        
        output_path = video_path.replace(".mp4", "_overlays.mp4")
        
        cmd = [
            self.ffmpeg,
            "-i", video_path,
            "-vf", ",".join(filter_parts),
            "-c:a", "copy",
            output_path
        ]
        
        await self._run_ffmpeg(cmd)
        return output_path
    
    async def _mix_audio(
        self,
        video_path: str,
        voiceover_path: str,
        music_path: str,
        output_settings: OutputSettings
    ) -> str:
        """Mix voiceover and background music."""
        
        output_path = video_path.replace(".mp4", "_final.mp4")
        
        # Music volume: -18dB (background), Voiceover: 0dB
        filter_complex = (
            f"[1:a]volume=0dB[vo];"
            f"[2:a]volume=-18dB[music];"
            f"[vo][music]amix=inputs=2:duration=first[a]"
        )
        
        cmd = [
            self.ffmpeg,
            "-i", video_path,
            "-i", voiceover_path,
            "-i", music_path,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ]
        
        await self._run_ffmpeg(cmd)
        return output_path
```

---

## 5. Safety & Compliance Guards

### 5.1 Content Validation

```python
# backend/app/services/ai/safety.py

FORBIDDEN_PATTERNS = [
    # Fair Housing Act violations
    r"\b(no\s+)?(families|children|kids)\s+(allowed|welcome|wanted)\b",
    r"\b(perfect\s+for|ideal\s+for|great\s+for)\s+(singles?|couples?|young\s+professionals?)\b",
    r"\b(christian|muslim|jewish|hindu|buddhist)\s+(neighborhood|community|area)\b",
    r"\b(walking\s+distance\s+to)\s+(church|mosque|synagogue|temple)\b",
    r"\bmaster\s+bedroom\b",  # Use "primary" instead
    
    # Investment/value claims
    r"\b(guaranteed|will)\s+(appreciate|increase\s+in\s+value)\b",
    r"\b(great|excellent|good)\s+investment\b",
    r"\b(can't|won't)\s+last\b",  # Urgency pressure
    
    # Discriminatory language
    r"\b(exclusive|prestigious)\s+(neighborhood|community|area)\b",
    r"\bsafe\s+(neighborhood|community|area)\b",  # Can imply racial bias
]

REQUIRED_DISCLAIMERS = {
    "investment_mention": "This is not financial advice. Consult with a real estate professional.",
}


class ContentValidator:
    def __init__(self):
        self.forbidden_patterns = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATTERNS]
    
    def validate_script(self, script: GeneratedScript) -> ValidationResult:
        """Validate generated script for compliance issues."""
        
        issues = []
        
        # Check all text content
        all_text = " ".join([
            script.hook,
            script.cta,
            *[scene.narration for scene in script.scenes],
            *[scene.on_screen_text for scene in script.scenes if scene.on_screen_text],
            script.caption
        ])
        
        for pattern in self.forbidden_patterns:
            matches = pattern.findall(all_text)
            if matches:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"Potentially non-compliant language detected: '{matches[0]}'",
                    suggestion="Please revise this language to be Fair Housing compliant."
                ))
        
        # Check for invented details
        # (This would compare against the original property listing)
        
        # Check text length for readability
        for scene in script.scenes:
            if scene.on_screen_text and len(scene.on_screen_text) > 40:
                issues.append(ValidationIssue(
                    severity="warning",
                    message=f"On-screen text too long for mobile: '{scene.on_screen_text}'",
                    suggestion="Shorten to under 40 characters for best mobile readability."
                ))
        
        return ValidationResult(
            is_valid=not any(i.severity == "error" for i in issues),
            issues=issues
        )
    
    def sanitize_text(self, text: str) -> str:
        """Automatically fix common issues."""
        
        # Replace "master bedroom" with "primary bedroom"
        text = re.sub(r"\bmaster\s+bedroom\b", "primary bedroom", text, flags=re.IGNORECASE)
        text = re.sub(r"\bmaster\s+suite\b", "primary suite", text, flags=re.IGNORECASE)
        text = re.sub(r"\bmaster\s+bath\b", "primary bath", text, flags=re.IGNORECASE)
        
        return text
```

### 5.2 Fact Verification

```python
# backend/app/services/ai/fact_checker.py

class FactChecker:
    """Ensures AI-generated content doesn't invent property details."""
    
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
    
    async def verify_script_facts(
        self,
        script: GeneratedScript,
        property_listing: PropertyListing
    ) -> FactCheckResult:
        """
        Verify that all facts in the script match the property listing.
        """
        
        known_facts = {
            "price": property_listing.listing_price,
            "bedrooms": property_listing.bedrooms,
            "bathrooms": property_listing.bathrooms,
            "square_feet": property_listing.square_feet,
            "address": property_listing.full_address,
            "features": property_listing.features,
            "status": property_listing.listing_status,
        }
        
        prompt = f"""
        Verify the following script against the known property facts.
        
        KNOWN FACTS:
        {json.dumps(known_facts, indent=2)}
        
        SCRIPT TO VERIFY:
        Hook: {script.hook}
        Scenes: {[s.narration for s in script.scenes]}
        CTA: {script.cta}
        Caption: {script.caption}
        
        Check for:
        1. Any invented details not in the known facts
        2. Any contradictions with the known facts
        3. Any exaggerations or embellishments
        
        Respond with:
        {{
            "is_factual": true/false,
            "issues": [
                {{
                    "type": "invented" | "contradiction" | "exaggeration",
                    "text": "the problematic text",
                    "explanation": "why this is an issue"
                }}
            ]
        }}
        """
        
        result = await self.llm.generate(
            system_prompt="You are a fact-checker for real estate content.",
            user_prompt=prompt,
            config=LLMConfig(temperature=0.1)  # Low temperature for accuracy
        )
        
        return FactCheckResult(**result)
```

---

## 6. Model Cost Optimization

### 6.1 Caching Strategy

```python
# backend/app/services/ai/cache.py

class AIResponseCache:
    """Cache AI responses to reduce API costs."""
    
    def __init__(self, redis_client: Redis, ttl_hours: int = 24):
        self.redis = redis_client
        self.ttl = ttl_hours * 3600
    
    def _generate_key(self, prompt_type: str, inputs: dict) -> str:
        """Generate cache key from prompt type and inputs."""
        content = json.dumps(inputs, sort_keys=True)
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"ai_cache:{prompt_type}:{hash_val}"
    
    async def get_cached_response(self, prompt_type: str, inputs: dict) -> Optional[dict]:
        """Get cached response if available."""
        key = self._generate_key(prompt_type, inputs)
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    async def cache_response(self, prompt_type: str, inputs: dict, response: dict):
        """Cache a response."""
        key = self._generate_key(prompt_type, inputs)
        await self.redis.setex(key, self.ttl, json.dumps(response))
```

### 6.2 Tiered Model Usage

```python
# Use cheaper models for simpler tasks

MODEL_TIERS = {
    "photo_analysis": "gpt-4-vision-preview",  # Requires vision
    "script_generation": "gpt-4-turbo",        # Creative, needs quality
    "scene_regeneration": "gpt-3.5-turbo",     # Simpler task
    "caption_generation": "gpt-3.5-turbo",     # Shorter output
    "shot_planning": "gpt-3.5-turbo",          # Structured output
    "layout_generation": "gpt-4-turbo",        # Complex visual reasoning
}
```

---

## 7. Error Handling & Fallbacks

```python
# backend/app/services/ai/fallbacks.py

class AIFallbackHandler:
    """Handle AI service failures gracefully."""
    
    DEFAULT_SCRIPTS = {
        "listing_tour": {
            "hook": "Welcome to your new home",
            "cta": "Contact us for a private showing"
        },
        "promo_video": {
            "hook": "I'm excited to share this with you",
            "cta": "Reach out today to learn more"
        }
    }
    
    async def with_fallback(
        self,
        primary_func: Callable,
        fallback_func: Optional[Callable] = None,
        default_value: Any = None,
        max_retries: int = 3
    ):
        """Execute with automatic fallback on failure."""
        
        for attempt in range(max_retries):
            try:
                return await primary_func()
            except RateLimitError:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                logger.error(f"AI call failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    if fallback_func:
                        return await fallback_func()
                    return default_value
        
        return default_value
```

