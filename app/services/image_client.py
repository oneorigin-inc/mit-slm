"""
HTTP client for calling badge image generation service
Replaces the old local image_generator module
"""
import httpx
import logging
from typing import Dict, Any, Optional, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)


async def generate_badge_with_text(
    short_title: str,
    institute: str = "",
    achievement_phrase: str = "",
    colors: Optional[dict] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Generate badge image with text overlay - returns base64 image and config

    Args:
        short_title: Short badge title text
        institute: Institution/organization name
        achievement_phrase: Achievement phrase or motto
        colors: Optional brand colors (primary, secondary, tertiary)

    Returns:
        Tuple of (base64 encoded image string, configuration dict)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.BADGE_IMAGE_SERVICE_URL}/api/v1/badge/generate-with-text",
                json={
                    "short_title": short_title,
                    "institute": institute,
                    "achievement_phrase": achievement_phrase,
                    "colors": colors
                }
            )
            response.raise_for_status()
            result = response.json()
            image_base64 = result.get("data", {}).get("base64", "")
            config = result.get("config", {})
            return image_base64, config
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling image service: {e}")
        raise Exception(f"Image service returned error: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Request error calling image service: {e}")
        raise Exception("Failed to connect to image service")
    except Exception as e:
        logger.error(f"Unexpected error calling image service: {e}")
        raise


async def generate_badge_with_icon(
    icon_name: str,
    colors: Optional[dict] = None,
    seed: Optional[int] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Generate badge image with icon - returns base64 image and config

    Args:
        icon_name: Icon filename (e.g., 'atom.png', 'trophy.png')
        colors: Optional brand colors (primary, secondary, tertiary)
        seed: Optional random seed for reproducibility

    Returns:
        Tuple of (base64 encoded image string, configuration dict)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.BADGE_IMAGE_SERVICE_URL}/api/v1/badge/generate-with-icon",
                json={
                    "icon_name": icon_name,
                    "colors": colors,
                    "seed": seed
                }
            )
            response.raise_for_status()
            result = response.json()
            image_base64 = result.get("data", {}).get("base64", "")
            config = result.get("config", {})
            return image_base64, config
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling image service: {e}")
        raise Exception(f"Image service returned error: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Request error calling image service: {e}")
        raise Exception("Failed to connect to image service")
    except Exception as e:
        logger.error(f"Unexpected error calling image service: {e}")
        raise
