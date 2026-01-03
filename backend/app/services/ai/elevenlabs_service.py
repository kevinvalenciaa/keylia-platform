"""ElevenLabs TTS service for voiceover generation."""

import asyncio
import tempfile
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


@dataclass
class Voice:
    """ElevenLabs voice representation."""

    voice_id: str
    name: str
    category: str
    description: str | None = None
    preview_url: str | None = None
    labels: dict[str, str] | None = None


@dataclass
class VoiceSettings:
    """Voice generation settings."""

    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True


@dataclass
class VoiceoverResult:
    """Result from voiceover generation."""

    audio_data: bytes
    audio_url: str | None = None
    duration_seconds: float | None = None
    characters_used: int = 0


class ElevenLabsService:
    """Service for generating voiceovers using ElevenLabs API."""

    BASE_URL = "https://api.elevenlabs.io/v1"
    DEFAULT_MODEL = "eleven_multilingual_v2"

    # Pre-configured voices for real estate content
    RECOMMENDED_VOICES = {
        "professional_female": "21m00Tcm4TlvDq8ikWAM",  # Rachel
        "professional_male": "29vD33N1CtxCmqQRPOHJ",  # Drew
        "friendly_female": "EXAVITQu4vr4xnSDxMaL",  # Bella
        "friendly_male": "ErXwobaYiN019PkySvjV",  # Antoni
        "warm_female": "MF3mGyEYCl7XYWbV9V6O",  # Emily
        "warm_male": "TxGEqnHWrfWFTfGW9XjX",  # Josh
    }

    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self._voices_cache: list[Voice] | None = None

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def generate_voiceover(
        self,
        text: str,
        voice_id: str | None = None,
        voice_settings: VoiceSettings | None = None,
        model_id: str | None = None,
    ) -> VoiceoverResult:
        """
        Generate voiceover audio from text.

        Args:
            text: The text to convert to speech
            voice_id: ElevenLabs voice ID (uses default if not provided)
            voice_settings: Voice generation settings
            model_id: Model to use (defaults to eleven_multilingual_v2)

        Returns:
            VoiceoverResult with audio data and metadata
        """
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not configured")

        # Use defaults
        voice_id = voice_id or self.RECOMMENDED_VOICES["professional_female"]
        voice_settings = voice_settings or VoiceSettings()
        model_id = model_id or self.DEFAULT_MODEL

        url = f"{self.BASE_URL}/text-to-speech/{voice_id}"

        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": voice_settings.stability,
                "similarity_boost": voice_settings.similarity_boost,
                "style": voice_settings.style,
                "use_speaker_boost": voice_settings.use_speaker_boost,
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                headers=self._get_headers(),
                json=payload,
            )

            if response.status_code != 200:
                error_detail = response.text
                raise Exception(f"ElevenLabs API error ({response.status_code}): {error_detail}")

            audio_data = response.content

            # Estimate duration (rough estimate based on word count)
            word_count = len(text.split())
            estimated_duration = word_count / 2.5  # Average speaking rate

            return VoiceoverResult(
                audio_data=audio_data,
                duration_seconds=estimated_duration,
                characters_used=len(text),
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def generate_voiceover_with_timestamps(
        self,
        text: str,
        voice_id: str | None = None,
        voice_settings: VoiceSettings | None = None,
    ) -> dict[str, Any]:
        """
        Generate voiceover with word-level timestamps for sync.

        Returns audio data along with alignment information.
        """
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not configured")

        voice_id = voice_id or self.RECOMMENDED_VOICES["professional_female"]
        voice_settings = voice_settings or VoiceSettings()

        url = f"{self.BASE_URL}/text-to-speech/{voice_id}/with-timestamps"

        payload = {
            "text": text,
            "model_id": self.DEFAULT_MODEL,
            "voice_settings": {
                "stability": voice_settings.stability,
                "similarity_boost": voice_settings.similarity_boost,
                "style": voice_settings.style,
                "use_speaker_boost": voice_settings.use_speaker_boost,
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                headers=self._get_headers(),
                json=payload,
            )

            if response.status_code != 200:
                error_detail = response.text
                raise Exception(f"ElevenLabs API error ({response.status_code}): {error_detail}")

            result = response.json()

            return {
                "audio_base64": result.get("audio_base64"),
                "alignment": result.get("alignment", {}),
                "characters_used": len(text),
            }

    async def list_voices(self, use_cache: bool = True) -> list[Voice]:
        """
        Get all available voices.

        Args:
            use_cache: Whether to use cached voices list

        Returns:
            List of available voices
        """
        if use_cache and self._voices_cache:
            return self._voices_cache

        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not configured")

        url = f"{self.BASE_URL}/voices"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._get_headers())

            if response.status_code != 200:
                raise Exception(f"Failed to fetch voices: {response.text}")

            data = response.json()
            voices = []

            for voice_data in data.get("voices", []):
                voice = Voice(
                    voice_id=voice_data["voice_id"],
                    name=voice_data["name"],
                    category=voice_data.get("category", "custom"),
                    description=voice_data.get("description"),
                    preview_url=voice_data.get("preview_url"),
                    labels=voice_data.get("labels"),
                )
                voices.append(voice)

            self._voices_cache = voices
            return voices

    async def get_recommended_voices(self) -> list[dict[str, Any]]:
        """
        Get recommended voices for real estate content.

        Returns curated list of voices suitable for property videos.
        """
        all_voices = await self.list_voices()

        # Filter to recommended voice IDs
        recommended_ids = set(self.RECOMMENDED_VOICES.values())
        recommended = []

        for voice in all_voices:
            if voice.voice_id in recommended_ids:
                # Find the label for this voice
                label = next(
                    (k for k, v in self.RECOMMENDED_VOICES.items() if v == voice.voice_id),
                    "custom",
                )
                recommended.append(
                    {
                        "voice_id": voice.voice_id,
                        "name": voice.name,
                        "label": label,
                        "category": voice.category,
                        "preview_url": voice.preview_url,
                        "description": voice.description,
                    }
                )

        return recommended

    async def get_voice_preview(self, voice_id: str) -> str | None:
        """Get preview audio URL for a voice."""
        voices = await self.list_voices()
        for voice in voices:
            if voice.voice_id == voice_id:
                return voice.preview_url
        return None

    async def generate_scene_voiceovers(
        self,
        scenes: list[dict[str, Any]],
        voice_id: str | None = None,
        voice_settings: VoiceSettings | None = None,
    ) -> list[dict[str, Any]]:
        """
        Generate voiceovers for multiple scenes in parallel.

        Args:
            scenes: List of scene dicts with 'narration_text' field
            voice_id: Voice to use for all scenes
            voice_settings: Voice settings

        Returns:
            List of scenes with 'voiceover_data' added
        """
        async def generate_for_scene(scene: dict) -> dict:
            narration = scene.get("narration_text", "")
            if not narration:
                return {**scene, "voiceover_data": None}

            try:
                result = await self.generate_voiceover(
                    text=narration,
                    voice_id=voice_id,
                    voice_settings=voice_settings,
                )
                return {
                    **scene,
                    "voiceover_data": {
                        "audio_data": result.audio_data,
                        "duration_seconds": result.duration_seconds,
                        "characters_used": result.characters_used,
                    },
                }
            except Exception as e:
                return {
                    **scene,
                    "voiceover_data": None,
                    "voiceover_error": str(e),
                }

        # Process scenes in parallel (with concurrency limit)
        semaphore = asyncio.Semaphore(3)  # Limit concurrent requests

        async def limited_generate(scene: dict) -> dict:
            async with semaphore:
                return await generate_for_scene(scene)

        tasks = [limited_generate(scene) for scene in scenes]
        results = await asyncio.gather(*tasks)

        return results

    def get_voice_for_style(self, gender: str = "female", style: str = "professional") -> str:
        """
        Get appropriate voice ID based on desired style.

        Args:
            gender: 'male' or 'female'
            style: 'professional', 'friendly', or 'warm'

        Returns:
            Voice ID string
        """
        key = f"{style}_{gender}"
        return self.RECOMMENDED_VOICES.get(key, self.RECOMMENDED_VOICES["professional_female"])


# Singleton instance
elevenlabs_service = ElevenLabsService()
