import time
import random
import logging
import uuid
import httpx
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.models.requests import BadgeRequest, RegenerationRequest, AppendDataRequest
from app.models.badge import BadgeResponse, BadgeValidated
from app.services.badge_generator import (
    generate_badge_metadata_async, 
    get_random_parameters,
    apply_regeneration_overrides,
    optimize_badge_text
)
from app.services.image_generator import generate_text_image_config, generate_icon_image_config
from app.utils.icon_matcher import get_icon_suggestions_for_badge
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory history
badge_history: List[Dict[str, Any]] = []

async def generate_badge_image(image_config: Dict[str, Any]) -> str:
    """Call the image generation API and return base64 image

    TODO: Replace hardcoded localhost:3001 with Docker Compose service URL in production
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:3001/api/v1/badge/generate",
                json=image_config,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result.get("data", {}).get("base64", "")
    except Exception as e:
        logger.error(f"Failed to generate badge image: {e}")
        return ""

@router.post("/generate-badge-suggestions", response_model=BadgeResponse)
async def generate_badge(request: BadgeRequest):
    """Generate a single badge with random parameter selection"""
    start_time = time.time()
    try:
        # Generate badge metadata with random parameters
        badge_json = await generate_badge_metadata_async(request)

        try:
            validated = BadgeValidated(
                badge_name=badge_json.get("badge_name", ""),
                badge_description=badge_json.get("badge_description", ""),
                criteria=badge_json.get("criteria", {}),  # This already contains {"narrative": "string"}
                raw_model_output=badge_json.get("raw_model_output", "")
            )
        except ValidationError as ve:
            logger.warning("Badge validation failed: %s", ve)
            raise HTTPException(status_code=502, detail=f"Badge schema validation error: {ve}")

        # Generate image configuration with random selection
        image_type = random.choice(["text_overlay", "icon_based"])
        logger.info(f"Selected image type: {image_type}")

        if image_type == "icon_based":
            icon_suggestions = await get_icon_suggestions_for_badge(
                badge_name=validated.badge_name,
                badge_description=validated.badge_description,
                custom_instructions=request.custom_instructions or "",
                top_k=3
            )
            
            image_config_wrapper = await generate_icon_image_config(
                validated.badge_name,
                validated.badge_description,
                icon_suggestions,
                request.institution or ""
            )
            
            image_config = image_config_wrapper.get("config", {})
            
        else:  # text_overlay
            optimized_text = await optimize_badge_text({
                "badge_name": validated.badge_name,
                "badge_description": validated.badge_description,
                "institution": request.institution or ""
            })
            
            image_config_wrapper = await generate_text_image_config(
                validated.badge_name,
                validated.badge_description,
                optimized_text,
                request.institution or ""
            )
            
            image_config = image_config_wrapper.get("config", {})

        # Generate badge ID
        badge_id = str(uuid.uuid4())

        # Generate badge image
        image_base64 = await generate_badge_image(image_config)

        # Transform to new JSON schema format
        result = BadgeResponse(
            credentialSubject={
                "achievement": {
                    "criteria": validated.criteria,  # This is already {"narrative": "string"} format
                    "description": validated.badge_description,
                    "image": {
                        "id": f"https://example.com/achievements/badge_{badge_id}/image",
                        "image_base64": image_base64
                    },
                    "name": validated.badge_name
                }
            },
            imageConfig=image_config,
            badge_id=badge_id
        )

        # Store in history with the full result for editing capability
        history_entry = {
            "id": len(badge_history) + 1,
            "timestamp": datetime.now().isoformat(),
            "course_input": (request.course_input[:100] + "...") if len(request.course_input) > 100 else request.course_input,
            "processed_course_input": badge_json.get("processed_course_input", request.course_input),
            "user_badge_style": request.badge_style,
            "user_badge_tone": request.badge_tone,
            "user_criterion_style": request.criterion_style,
            "user_badge_level": request.badge_level,
            "custom_instructions": request.custom_instructions,
            "institution": request.institution,
            "selected_image_type": image_type,
            "selected_parameters": badge_json.get("selected_parameters", {}),
            "badge_id": badge_id,
            "result": result,  # Store the full result for editing
            "generation_time": time.time() - start_time
        }
        badge_history.append(history_entry)
        
        if len(badge_history) > 50:
            badge_history.pop(0)

        selected_params = badge_json.get("selected_parameters", {})
        logger.info(f"Generated badge ID {badge_id}: '{validated.badge_name}' with parameters: {selected_params}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /generate-badge-suggestions: %s", e)
        raise HTTPException(status_code=500, detail=f"Badge generation error: {str(e)}")

@router.post("/regenerate_badge", response_model=BadgeResponse)
async def regenerate_badge(request: RegenerationRequest):
    """Regenerate badge with specific parameter overrides"""
    start_time = time.time()
    try:
        # Create a mock request object for consistency
        mock_request = BadgeRequest(
            course_input=request.course_input,
            badge_style="",  # Will be randomly overridden
            badge_tone="",   # Will be randomly overridden
            criterion_style="",  # Will be randomly overridden
            badge_level="",  # Will be randomly overridden
            custom_instructions=request.custom_instructions,
            institution=request.institution
        )
        
        # Get current random parameters
        current_params = get_random_parameters(mock_request)
        
        # Apply regeneration overrides
        regeneration_map = {param: True for param in request.regenerate_parameters}
        updated_params = apply_regeneration_overrides(current_params, regeneration_map)
        
        # Update mock request with new parameters
        mock_request.badge_style = updated_params['badge_style']
        mock_request.badge_tone = updated_params['badge_tone']
        mock_request.criterion_style = updated_params['criterion_style']
        mock_request.badge_level = updated_params['badge_level']
        
        # Generate badge with updated parameters
        badge_json = await generate_badge_metadata_async(mock_request)

        try:
            validated = BadgeValidated(
                badge_name=badge_json.get("badge_name", ""),
                badge_description=badge_json.get("badge_description", ""),
                criteria=badge_json.get("criteria", {}),  # This already contains {"narrative": "string"}
                raw_model_output=badge_json.get("raw_model_output", "")
            )
        except ValidationError as ve:
            logger.warning("Badge validation failed: %s", ve)
            raise HTTPException(status_code=502, detail=f"Badge schema validation error: {ve}")

        # Generate image configuration
        image_type = random.choice(["text_overlay", "icon_based"])
        
        if image_type == "icon_based":
            icon_suggestions = await get_icon_suggestions_for_badge(
                badge_name=validated.badge_name,
                badge_description=validated.badge_description,
                custom_instructions=request.custom_instructions or "",
                top_k=3
            )
            
            image_config_wrapper = await generate_icon_image_config(
                validated.badge_name,
                validated.badge_description,
                icon_suggestions,
                request.institution or ""
            )
            
            image_config = image_config_wrapper.get("config", {})
            
        else:  # text_overlay
            optimized_text = await optimize_badge_text({
                "badge_name": validated.badge_name,
                "badge_description": validated.badge_description,
                "institution": request.institution or ""
            })
            
            image_config_wrapper = await generate_text_image_config(
                validated.badge_name,
                validated.badge_description,
                optimized_text,
                request.institution or ""
            )
            
            image_config = image_config_wrapper.get("config", {})

        # Generate badge ID
        badge_id = str(uuid.uuid4())

        # Transform to new JSON schema format
        result = BadgeResponse(
            credentialSubject={
                "achievement": {
                    "criteria": validated.criteria,  # This is already {"narrative": "string"} format
                    "description": validated.badge_description,
                    "image": {
                        "id": f"https://example.com/achievements/badge_{badge_id}/image"
                    },
                    "name": validated.badge_name
                }
            },
            imageConfig=image_config,
            badge_id=badge_id
        )

        logger.info(f"Regenerated badge ID {badge_id} with overridden parameters: {request.regenerate_parameters}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /regenerate_badge: %s", e)
        raise HTTPException(status_code=500, detail=f"Badge regeneration error: {str(e)}")

@router.post("/edit-badge-metadata")
async def edit_badge_metadata(request: AppendDataRequest):
    """Append data to an existing badge result from history"""
    try:
        # Find the badge in history by ID
        target_badge = None
        for badge in badge_history:
            if badge.get("id") == request.badge_id:
                target_badge = badge
                break
                
        if not target_badge:
            raise HTTPException(
                status_code=404,
                detail=f"Badge with ID {request.badge_id} not found in history"
            )
            
        # Get the existing result
        existing_result = target_badge.get("result")
        if not existing_result:
            raise HTTPException(
                status_code=400,
                detail=f"Badge with ID {request.badge_id} has no result data to append to"
            )
            
        # Convert existing result to dict if it's a Pydantic model
        if hasattr(existing_result, 'dict'):
            result_dict = existing_result.dict()
        elif hasattr(existing_result, '__dict__'):
            result_dict = existing_result.__dict__
        else:
            result_dict = dict(existing_result) if isinstance(existing_result, dict) else {}
            
        # Append the new data to badge_data
        updated_result = result_dict.copy()
        if 'badge_data' in updated_result:
            updated_result['badge_data'].update(request.append_data)
        else:
            # Fallback if badge_data doesn't exist
            updated_result.update(request.append_data)
            
        # Update the badge history entry with the new result
        target_badge["result"] = updated_result
        target_badge["last_updated"] = datetime.now().isoformat()
        
        return {
            "message": f"Data successfully appended to badge {request.badge_id}",
            "badge_id": request.badge_id,
            "updated_result": updated_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /edit-badge-metadata: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to append data: {str(e)}")

@router.post("/optimize_badge_text")
async def optimize_badge_text_endpoint(badge_data: dict, max_title_chars: int = 25):
    """Optimize badge text for image overlay"""
    return await optimize_badge_text(badge_data, max_title_chars)

@router.get("/badge_history")
async def get_badge_history():
    """Get the recent badge generation history."""
    return {"history": badge_history, "total_count": len(badge_history)}

@router.delete("/badge_history")
async def clear_badge_history():
    """Clear the badge generation history."""
    global badge_history
    badge_history.clear() 
    return {"message": "Badge history cleared successfully"}

@router.get("/styles")
async def get_styles():
    """Get available badge styles and their descriptions."""
    return {
        "badge_styles": settings.STYLE_DESCRIPTIONS,
        "badge_tones": settings.TONE_DESCRIPTIONS,
        "criterion_styles": settings.CRITERION_TEMPLATES,
        "badge_levels": settings.LEVEL_DESCRIPTIONS
    }

