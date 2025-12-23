"""
Simplified client for external badge image generation service
Handles both text_overlay and icon_based badge images
"""
import httpx
import logging
import json
import time
import copy
from typing import Dict, Any, Optional, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)


def _log_outgoing_request(method: str, url: str, headers: Dict[str, Any], payload: Dict[str, Any]):
    """
    Log outgoing API request in systematic format (excludes base64 data unless ENABLE_LOG_BASE64_DATA is True)
    """
    # If base64 logging is enabled, log payload as-is
    if settings.ENABLE_LOG_BASE64_DATA:
        sanitized_payload = payload
    else:
        # Deep copy to avoid modifying the original payload
        sanitized_payload = copy.deepcopy(payload)
        if "image_configuration" in sanitized_payload and isinstance(sanitized_payload["image_configuration"], dict):
            img_config = sanitized_payload["image_configuration"]
            if "logo" in img_config and img_config["logo"]:
                img_config["logo"] = "<base64_data_excluded_from_log>"
    
    logger.info('--------------------------------------------------------------')
    logger.info(
        f"""Internal Service Call (Outgoing Request) >>>
      ######################################################
      service             Badge Image Generation Service
      method              {method}
      endpoint            {url}
      headers             {json.dumps(headers, indent=1)}
      payload             {json.dumps(sanitized_payload, indent=1)}
      ######################################################"""
    )


def _log_outgoing_response(status_code: int, response_time: float, response_body: Dict[str, Any]):
    """
    Log outgoing API response in systematic format (excludes base64 data unless ENABLE_LOG_BASE64_DATA is True)
    """
    # If base64 logging is enabled, log response as-is
    if settings.ENABLE_LOG_BASE64_DATA:
        sanitized_response = response_body if response_body else {}
    else:
        # Deep copy to avoid modifying the original response
        sanitized_response = copy.deepcopy(response_body) if response_body else {}
        if "data" in sanitized_response and isinstance(sanitized_response["data"], dict):
            if "base64" in sanitized_response["data"] and sanitized_response["data"]["base64"]:
                sanitized_response["data"]["base64"] = "<base64_data_excluded_from_log>"
    
    logger.info(
        f"""Internal Service Call (Response Received) >>>
      ######################################################
      service             Badge Image Generation Service
      status_code         {status_code}
      response_time       {response_time:.4f}s
      response_data       {json.dumps(sanitized_response, indent=1)}
      ######################################################"""
    )
    logger.info('--------------------------------------------------------------')


async def call_badge_image_service(
    image_type: str,  # "text_overlay" or "icon_based"
    badge_name: str,
    badge_description: str,
    institution: Optional[str] = None,
    institute_url: Optional[str] = None,
    image_configuration: Any = None,
    short_title: Optional[str] = None,  # For text_overlay
    achievement_phrase: Optional[str] = None,  # For text_overlay
) -> Tuple[str, Dict[str, Any]]:
    """
    Call external badge image generation service
    Internally routes to appropriate endpoint based on image_type:
    - text_overlay → /badge/generate-with-text
    - icon_based → /badge/generate-with-icon
    
    Args:
        image_type: "text_overlay" or "icon_based"
        badge_name: Badge title
        badge_description: Badge description
        institution: Institution name
        institute_url: Institution URL (for color scraping)
        image_configuration: Image config object
        short_title: Optimized short title (for text_overlay only)
        achievement_phrase: Optimized phrase (for text_overlay only)
    
    Returns:
        Tuple of (base64 encoded image, image config dict)
    """
    try:
        # Decide which endpoint to call based on image_type
        if image_type == "text_overlay":
            return await _generate_text_badge(
                short_title=short_title or badge_name,
                achievement_phrase=achievement_phrase or "Achievement Unlocked",
                institution=institution,
                institute_url=institute_url,
                image_configuration=image_configuration
            )
        
        elif image_type == "icon_based":
            return await _generate_icon_badge(
                badge_name=badge_name,
                badge_description=badge_description,
                institution=institution,
                institute_url=institute_url,
                image_configuration=image_configuration
            )
        
        else:
            logger.error(f"Invalid image_type: {image_type}. Must be 'text_overlay' or 'icon_based'")
            return "", {}
            
    except Exception as e:
        logger.error(f"Unexpected error in call_badge_image_service: {e}")
        return "", {}


async def _generate_text_badge(
    short_title: str,
    achievement_phrase: str,
    institution: Optional[str] = None,
    institute_url: Optional[str] = None,
    image_configuration: Any = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Call /badge/generate-with-text endpoint for text overlay badges
    """
    try:
        # Build payload matching exact structure
        payload = {
            "image_type": "text_overlay",
            "institution": institution or "",
            "institute_url": institute_url or "",
            "short_title": short_title,
            "achievement_phrase": achievement_phrase,
            "image_configuration": {}
        }
        
        # Add image configuration if provided
        if image_configuration:
            payload["image_configuration"] = {
                "primary_color": image_configuration.primary_color or "",
                "secondary_color": image_configuration.secondary_color or "",
                "border_color": image_configuration.border_color or "",
                "border_width": image_configuration.border_width if image_configuration.border_width else 0,
                "shape": image_configuration.shape or "",
                "logo": image_configuration.logo or ""
            }
        
        url = f"{settings.BADGE_IMAGE_SERVICE_URL}/api/v1/badge/generate-with-text"
        
        # Log outgoing request
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            _log_outgoing_request(
                method="POST",
                url=url,
                headers=dict(client.headers),
                payload=payload
            )
            
            response = await client.post(url, json=payload)
            response_time = time.time() - start_time
            
            response.raise_for_status()
            result = response.json()
            
            # Log outgoing response
            _log_outgoing_response(
                status_code=response.status_code,
                response_time=response_time,
                response_body=result
            )
            
            image_base64 = result.get("data", {}).get("base64", "")
            image_config = result.get("config", {})
            
            logger.info("Successfully generated text_overlay badge image")
            return image_base64, image_config
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Text badge service returned error {e.response.status_code}: {e.response.text}")
        return "", {}
    except httpx.ConnectError as e:
        logger.error(f"Cannot connect to text badge service: {e}")
        return "", {}
    except Exception as e:
        logger.error(f"Unexpected error generating text badge: {e}")
        return "", {}


async def _generate_icon_badge(
    badge_name: str,
    badge_description: str,
    institution: Optional[str] = None,
    institute_url: Optional[str] = None,
    image_configuration: Any = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Call /badge/generate-with-icon endpoint for icon-based badges
    """
    try:
        # Build payload matching exact structure
        payload = {
            "image_type": "icon_based",
            "badge_name": badge_name,
            "badge_description": badge_description,
            "institution": institution or "",
            "institute_url": institute_url or "",
            "image_configuration": {}
        }
        
        # Add image configuration if provided
        if image_configuration:
            payload["image_configuration"] = {
                "primary_color": image_configuration.primary_color or "",
                "secondary_color": image_configuration.secondary_color or "",
                "border_color": image_configuration.border_color or "",
                "border_width": image_configuration.border_width if image_configuration.border_width else 0,
                "shape": image_configuration.shape or "",
                "logo": image_configuration.logo or ""
            }
        
        url = f"{settings.BADGE_IMAGE_SERVICE_URL}/api/v1/badge/generate-with-icon"
        
        # Log outgoing request
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            _log_outgoing_request(
                method="POST",
                url=url,
                headers=dict(client.headers),
                payload=payload
            )
            
            response = await client.post(url, json=payload)
            response_time = time.time() - start_time
            
            response.raise_for_status()
            result = response.json()
            
            # Log outgoing response
            _log_outgoing_response(
                status_code=response.status_code,
                response_time=response_time,
                response_body=result
            )
            
            image_base64 = result.get("data", {}).get("base64", "")
            image_config = result.get("config", {})
            
            logger.info("Successfully generated icon_based badge image")
            return image_base64, image_config
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Icon badge service returned error {e.response.status_code}: {e.response.text}")
        return "", {}
    except httpx.ConnectError as e:
        logger.error(f"Cannot connect to icon badge service: {e}")
        return "", {}
    except Exception as e:
        logger.error(f"Unexpected error generating icon badge: {e}")
        return "", {}

