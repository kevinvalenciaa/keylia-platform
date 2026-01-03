"""
Input sanitization utilities for AI prompts.

This module provides functions to sanitize user input before including
it in AI prompts to prevent prompt injection attacks and ensure
safe content generation.
"""

import html
import re
from typing import Any


# Maximum lengths for various input types
MAX_LENGTHS = {
    "address": 500,
    "description": 5000,
    "feature": 200,
    "city": 100,
    "neighborhood": 100,
    "headline": 300,
    "default": 1000,
}

# Characters that could be used for prompt injection
DANGEROUS_PATTERNS = [
    # Instruction overrides
    r"ignore (all )?(previous|prior|above) (instructions?|prompts?)",
    r"disregard (all )?(previous|prior|above)",
    r"forget (all )?(previous|prior|above)",
    r"override (all )?(previous|prior|above)",
    # System prompt extraction attempts
    r"(show|reveal|display|print|output) (your|the|my)? ?(system|initial) ?(prompt|instructions?)",
    r"what (are|is) your (system|initial) (prompt|instructions?)",
    # Role manipulation
    r"you are now",
    r"act as if",
    r"pretend (to be|you are)",
    r"assume the role",
    # Delimiter injection
    r"```system",
    r"<system>",
    r"</system>",
    r"\[INST\]",
    r"\[/INST\]",
]


def sanitize_text(
    text: str | None,
    max_length: int | None = None,
    field_type: str = "default",
    allow_newlines: bool = True,
) -> str:
    """
    Sanitize text input for use in AI prompts.

    Args:
        text: The text to sanitize
        max_length: Maximum allowed length (overrides field_type default)
        field_type: Type of field for default max_length
        allow_newlines: Whether to preserve newlines

    Returns:
        Sanitized text
    """
    if text is None:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # Trim whitespace
    text = text.strip()

    # Handle empty string
    if not text:
        return ""

    # Escape HTML entities to prevent any injection via special chars
    text = html.escape(text, quote=True)

    # Remove or neutralize dangerous patterns (case-insensitive)
    for pattern in DANGEROUS_PATTERNS:
        text = re.sub(pattern, "[FILTERED]", text, flags=re.IGNORECASE)

    # Remove control characters except newlines and tabs
    if allow_newlines:
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    else:
        text = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text)
        text = re.sub(r"\s+", " ", text)

    # Apply length limit
    length_limit = max_length or MAX_LENGTHS.get(field_type, MAX_LENGTHS["default"])
    if len(text) > length_limit:
        text = text[:length_limit] + "..."

    return text


def sanitize_listing_data(listing_data: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize all fields in a listing data dictionary.

    Args:
        listing_data: Raw listing data from user input

    Returns:
        Sanitized listing data safe for AI prompts
    """
    sanitized = {}

    # String fields with their types
    string_fields = {
        "address": "address",
        "address_line1": "address",
        "city": "city",
        "state": "city",
        "zip": "city",
        "neighborhood": "neighborhood",
        "headline": "headline",
        "description": "description",
        "property_type": "default",
    }

    for field, field_type in string_fields.items():
        if field in listing_data:
            sanitized[field] = sanitize_text(
                listing_data.get(field), field_type=field_type
            )

    # Numeric fields - convert to safe types
    numeric_fields = ["price", "bedrooms", "bathrooms", "square_feet", "sqft", "year_built"]
    for field in numeric_fields:
        if field in listing_data:
            value = listing_data.get(field)
            if value is not None:
                try:
                    # Convert to float then int to handle various input formats
                    sanitized[field] = int(float(str(value).replace(",", "").replace("$", "")))
                except (ValueError, TypeError):
                    sanitized[field] = 0

    # List fields (features, amenities)
    list_fields = ["features", "amenities"]
    for field in list_fields:
        if field in listing_data and isinstance(listing_data[field], list):
            sanitized[field] = [
                sanitize_text(item, field_type="feature")
                for item in listing_data[field][:20]  # Limit number of items
                if item
            ]

    # Copy over any remaining safe fields
    safe_passthrough = ["latitude", "longitude", "lot_size_sqft"]
    for field in safe_passthrough:
        if field in listing_data:
            value = listing_data.get(field)
            if isinstance(value, (int, float)):
                sanitized[field] = value

    return sanitized


def sanitize_style_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize style settings for video generation.

    Args:
        settings: Raw style settings

    Returns:
        Sanitized style settings
    """
    sanitized = {}

    # Whitelist allowed values for each setting
    allowed_values = {
        "tone": ["luxury", "cozy", "modern", "minimal", "bold"],
        "pace": ["slow", "moderate", "fast"],
        "music_vibe": ["cinematic", "upbeat", "relaxing", "dramatic"],
        "platform": ["instagram_reels", "tiktok", "youtube_shorts"],
        "aspect_ratio": ["9:16", "16:9", "1:1", "4:5"],
        "video_model": ["kling", "kling_pro", "kling_v2", "veo3", "veo3_fast", "minimax", "runway"],
    }

    for key, allowed in allowed_values.items():
        value = settings.get(key)
        if value and str(value).lower() in allowed:
            sanitized[key] = str(value).lower()
        elif allowed:
            sanitized[key] = allowed[0]  # Use first as default

    # Numeric settings with bounds
    duration = settings.get("duration_seconds", 30)
    if isinstance(duration, (int, float)):
        sanitized["duration_seconds"] = max(15, min(60, int(duration)))
    else:
        sanitized["duration_seconds"] = 30

    return sanitized


def sanitize_voice_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize voice settings for voiceover generation.

    Args:
        settings: Raw voice settings

    Returns:
        Sanitized voice settings
    """
    sanitized = {}

    # Boolean enabled flag
    sanitized["enabled"] = bool(settings.get("enabled", True))

    # Whitelist language codes
    allowed_languages = ["en-US", "en-GB", "en-AU", "es-ES", "es-MX", "fr-FR"]
    language = settings.get("language", "en-US")
    if language in allowed_languages:
        sanitized["language"] = language
    else:
        sanitized["language"] = "en-US"

    # Gender
    gender = settings.get("gender", "female")
    if gender in ["female", "male"]:
        sanitized["gender"] = gender
    else:
        sanitized["gender"] = "female"

    # Style
    allowed_styles = ["friendly", "professional", "energetic", "calm"]
    style = settings.get("style", "friendly")
    if style in allowed_styles:
        sanitized["style"] = style
    else:
        sanitized["style"] = "friendly"

    # Voice ID - alphanumeric only
    voice_id = settings.get("voice_id")
    if voice_id and re.match(r"^[a-zA-Z0-9_-]+$", str(voice_id)):
        sanitized["voice_id"] = str(voice_id)[:50]

    return sanitized


def create_safe_prompt_context(
    listing_data: dict[str, Any],
    style_settings: dict[str, Any] | None = None,
    voice_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a fully sanitized context for AI prompt generation.

    This is the main entry point for creating safe prompt data
    from user input.

    Args:
        listing_data: Raw listing data
        style_settings: Raw style settings
        voice_settings: Raw voice settings

    Returns:
        Dictionary with all sanitized data ready for prompt construction
    """
    return {
        "listing": sanitize_listing_data(listing_data),
        "style": sanitize_style_settings(style_settings or {}),
        "voice": sanitize_voice_settings(voice_settings or {}),
    }
