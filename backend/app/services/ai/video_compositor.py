"""Video composition service using FFmpeg."""

import asyncio
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

import httpx

from app.config import settings


class VideoCompositor:
    """
    Service for compositing final videos from fal.ai generated clips.
    
    Uses FFmpeg to:
    - Concatenate video clips
    - Add transitions
    - Overlay text and graphics
    - Mix audio (voiceover + music)
    - Encode final output
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg = ffmpeg_path
        self.http_client = httpx.AsyncClient(timeout=120.0)

    async def composite_property_tour(
        self,
        scene_clips: list[dict[str, Any]],
        voiceover_url: Optional[str],
        music_url: Optional[str],
        brand_kit: dict[str, Any],
        output_settings: dict[str, Any],
    ) -> str:
        """
        Create a complete property tour video.
        
        Args:
            scene_clips: List of {"video_url": str, "on_screen_text": str, "duration": float}
            voiceover_url: URL to voiceover audio file
            music_url: URL to background music file
            brand_kit: Brand settings (colors, fonts, logo)
            output_settings: Resolution, format, etc.
        
        Returns:
            URL to the final composed video
        """
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Step 1: Download all clips
            clip_paths = await self._download_clips(scene_clips, temp_path)
            
            # Step 2: Download audio files
            voiceover_path = None
            if voiceover_url:
                voiceover_path = await self._download_file(
                    voiceover_url, temp_path / "voiceover.mp3"
                )
            
            music_path = None
            if music_url:
                music_path = await self._download_file(
                    music_url, temp_path / "music.mp3"
                )
            
            # Step 3: Concatenate video clips with crossfade transitions
            concat_path = temp_path / "concat.mp4"
            await self._concatenate_with_transitions(
                clip_paths, concat_path, transition_duration=0.5
            )
            
            # Step 4: Add text overlays
            overlay_path = temp_path / "overlay.mp4"
            await self._add_text_overlays(
                concat_path, overlay_path, scene_clips, brand_kit
            )
            
            # Step 5: Add logo watermark
            if brand_kit.get("logo_url"):
                logo_path = await self._download_file(
                    brand_kit["logo_url"], temp_path / "logo.png"
                )
                watermark_path = temp_path / "watermark.mp4"
                await self._add_logo_watermark(overlay_path, logo_path, watermark_path)
                overlay_path = watermark_path
            
            # Step 6: Mix audio
            final_path = temp_path / "final.mp4"
            await self._mix_audio(
                video_path=overlay_path,
                voiceover_path=voiceover_path,
                music_path=music_path,
                output_path=final_path,
            )
            
            # Step 7: Upload to S3
            output_url = await self._upload_to_s3(final_path)
            
            return output_url

    async def _download_clips(
        self,
        scene_clips: list[dict],
        temp_dir: Path,
    ) -> list[Path]:
        """Download all video clips in parallel."""
        
        tasks = []
        for i, clip in enumerate(scene_clips):
            output_path = temp_dir / f"clip_{i:03d}.mp4"
            task = self._download_file(clip["video_url"], output_path)
            tasks.append(task)
        
        paths = await asyncio.gather(*tasks)
        return list(paths)

    async def _download_file(self, url: str, output_path: Path) -> Path:
        """Download a file from URL."""
        
        response = await self.http_client.get(url)
        response.raise_for_status()
        
        output_path.write_bytes(response.content)
        return output_path

    async def _concatenate_with_transitions(
        self,
        clip_paths: list[Path],
        output_path: Path,
        transition_duration: float = 0.5,
    ) -> None:
        """Concatenate clips with crossfade transitions."""
        
        if len(clip_paths) == 1:
            # Just copy the single clip
            subprocess.run([
                self.ffmpeg, "-i", str(clip_paths[0]),
                "-c", "copy", str(output_path)
            ], check=True)
            return
        
        # Build complex filter for crossfade transitions
        filter_parts = []
        
        # First, scale all inputs to same size
        for i in range(len(clip_paths)):
            filter_parts.append(f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]")
        
        # Then apply crossfade transitions
        prev = "[v0]"
        for i in range(1, len(clip_paths)):
            if i == len(clip_paths) - 1:
                output = "[vout]"
            else:
                output = f"[v{i}out]"
            
            # Calculate offset for crossfade
            offset = i * 4.5  # 5 second clips - 0.5 second overlap
            filter_parts.append(
                f"{prev}[v{i}]xfade=transition=fade:duration={transition_duration}:offset={offset}{output}"
            )
            prev = output
        
        filter_complex = ";".join(filter_parts)
        
        # Build FFmpeg command
        cmd = [self.ffmpeg, "-y"]
        for path in clip_paths:
            cmd.extend(["-i", str(path)])
        
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            str(output_path)
        ])
        
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: subprocess.run(cmd, check=True)
        )

    async def _add_text_overlays(
        self,
        input_path: Path,
        output_path: Path,
        scene_clips: list[dict],
        brand_kit: dict,
    ) -> None:
        """Add text overlays to video."""
        
        # Build drawtext filters for each scene
        filters = []
        current_time = 0.0
        
        primary_color = brand_kit.get("primary_color", "#FFFFFF").replace("#", "")
        font = brand_kit.get("heading_font", "Arial")
        
        for clip in scene_clips:
            text = clip.get("on_screen_text", "")
            duration = clip.get("duration", 5.0)
            
            if text:
                # Escape special characters
                text = text.replace("'", "\\'").replace(":", "\\:")
                
                filter_str = (
                    f"drawtext=text='{text}':"
                    f"fontsize=64:"
                    f"fontcolor=white:"
                    f"borderw=3:"
                    f"bordercolor=black:"
                    f"x=(w-text_w)/2:"
                    f"y=h-250:"
                    f"enable='between(t,{current_time},{current_time + duration - 0.5})'"
                )
                filters.append(filter_str)
            
            current_time += duration - 0.5  # Account for transition overlap
        
        if not filters:
            # No text overlays, just copy
            subprocess.run([
                self.ffmpeg, "-i", str(input_path),
                "-c", "copy", str(output_path)
            ], check=True)
            return
        
        filter_str = ",".join(filters)
        
        cmd = [
            self.ffmpeg, "-y",
            "-i", str(input_path),
            "-vf", filter_str,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "copy",
            str(output_path)
        ]
        
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: subprocess.run(cmd, check=True)
        )

    async def _add_logo_watermark(
        self,
        video_path: Path,
        logo_path: Path,
        output_path: Path,
    ) -> None:
        """Add logo watermark to bottom right."""
        
        cmd = [
            self.ffmpeg, "-y",
            "-i", str(video_path),
            "-i", str(logo_path),
            "-filter_complex",
            "[1:v]scale=120:-1[logo];[0:v][logo]overlay=W-w-40:H-h-180",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "copy",
            str(output_path)
        ]
        
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: subprocess.run(cmd, check=True)
        )

    async def _mix_audio(
        self,
        video_path: Path,
        voiceover_path: Optional[Path],
        music_path: Optional[Path],
        output_path: Path,
    ) -> None:
        """Mix voiceover and background music with video."""
        
        inputs = ["-i", str(video_path)]
        filter_parts = []
        
        if voiceover_path:
            inputs.extend(["-i", str(voiceover_path)])
        
        if music_path:
            inputs.extend(["-i", str(music_path)])
        
        if voiceover_path and music_path:
            # Mix voiceover (full volume) with music (-18dB)
            filter_complex = (
                "[1:a]volume=1.0[vo];"
                "[2:a]volume=0.15[music];"
                "[vo][music]amix=inputs=2:duration=first[aout]"
            )
            map_args = ["-map", "0:v", "-map", "[aout]"]
        elif voiceover_path:
            filter_complex = "[1:a]volume=1.0[aout]"
            map_args = ["-map", "0:v", "-map", "[aout]"]
        elif music_path:
            filter_complex = "[1:a]volume=0.3[aout]"
            map_args = ["-map", "0:v", "-map", "[aout]"]
        else:
            # No audio to mix
            subprocess.run([
                self.ffmpeg, "-i", str(video_path),
                "-c", "copy", str(output_path)
            ], check=True)
            return
        
        cmd = [
            self.ffmpeg, "-y",
            *inputs,
            "-filter_complex", filter_complex,
            *map_args,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path)
        ]
        
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: subprocess.run(cmd, check=True)
        )

    async def _upload_to_s3(self, file_path: Path) -> str:
        """Upload file to S3 and return URL."""
        
        import boto3
        from botocore.config import Config
        
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            config=Config(signature_version="s3v4"),
        )
        
        # Generate unique key
        import uuid
        key = f"renders/{uuid.uuid4()}/{file_path.name}"
        
        # Upload file
        s3_client.upload_file(
            str(file_path),
            settings.S3_BUCKET_NAME,
            key,
            ExtraArgs={"ContentType": "video/mp4"},
        )
        
        # Generate URL
        if settings.S3_BUCKET_URL:
            return f"{settings.S3_BUCKET_URL}/{key}"
        else:
            return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()

