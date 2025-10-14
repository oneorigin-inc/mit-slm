"""
HTTP client for calling badge image generation service
Replaces the old local image_generator module
"""
import httpx
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


async def generate_badge_with_text(
    badge_name: str,
    badge_description: str,
    optimized_text: dict,
    institution: str = "",
    institution_colors: Optional[dict] = None
) -> str:
    """
    Generate badge image with text overlay - returns base64 image

    Args:
        badge_name: Name of the badge
        badge_description: Description of the badge
        optimized_text: Optimized text from optimize_badge_text function
        institution: Institution name
        institution_colors: Optional institution brand colors

    Returns:
        Base64 encoded image string
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.BADGE_IMAGE_SERVICE_URL}/api/v1/badge/generate-with-text",
                json={
                    "badge_name": badge_name,
                    "badge_description": badge_description,
                    "optimized_text": optimized_text,
                    "institution": institution,
                    "institution_colors": institution_colors
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("data", {}).get("base64", "")
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
    badge_name: str,
    badge_description: str,
    icon_suggestions: dict,
    institution: str = "",
    institution_colors: Optional[dict] = None
) -> str:
    """
    Generate badge image with icon - returns base64 image

    Args:
        badge_name: Name of the badge
        badge_description: Description of the badge
        icon_suggestions: Icon suggestions from get_icon_suggestions_for_badge
        institution: Institution name
        institution_colors: Optional institution brand colors

    Returns:
        Base64 encoded image string
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            json={
                    "badge_name": badge_name,
                    "badge_description": badge_description,
                    "icon_suggestions": icon_suggestions,
                    "institution": institution,
                    "institution_colors": institution_colors
                }
            print("Request JSON:", json)
            response = await client.post(
                f"{settings.BADGE_IMAGE_SERVICE_URL}/api/v1/badge/generate-with-icon",
                json={
                    "badge_name": badge_name,
                    "badge_description": badge_description,
                    "icon_suggestions": icon_suggestions,
                    "institution": institution,
                    "institution_colors": institution_colors
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("data", {}).get("base64", "")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling image service: {e}")
        raise Exception(f"Image service returned error: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Request error calling image service: {e}")
        raise Exception("Failed to connect to image service")
    except Exception as e:
        logger.error(f"Unexpected error calling image service: {e}")
        raise
