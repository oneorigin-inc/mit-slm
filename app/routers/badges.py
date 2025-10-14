import time
import random
import logging
import json
import re
import httpx
from datetime import datetime
from typing import AsyncGenerator, List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError
import uuid

from app.models.requests import BadgeRequest, RegenerationRequest, AppendDataRequest, FieldRegenerateRequest
from app.models.badge import BadgeResponse, BadgeValidated
from app.services.badge_generator import (
    generate_badge_metadata_async,
    generate_badge_metadata_stream_async,
    get_random_parameters,
    apply_regeneration_overrides,
    optimize_badge_text,
    extract_json_from_response
)
from app.services.image_client import generate_badge_with_text, generate_badge_with_icon
from app.services.text_processor import process_course_input
from app.utils.icon_matcher import get_icon_suggestions_for_badge
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory history
badge_history: List[Dict[str, Any]] = []


def log_response(operation: str, success: bool, request_id: Optional[str] = None):
    """Log API response"""
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"{operation} - {status}" + (f" (Request ID: {request_id})" if request_id else ""))

def handle_error(error: Exception, operation: str, request_id: Optional[str] = None) -> HTTPException:
    """Handle and log errors"""
    logger.exception(f"{operation} failed: {error}")
    return HTTPException(status_code=500, detail=f"{operation} failed: {str(error)}")


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

            # Extract icon name from suggestions
            icon_name = icon_suggestions.get('suggested_icon', {}).get('name', 'trophy.png')

            image_base64, image_config = await generate_badge_with_icon(
                icon_name=icon_name
            )

        else:  # text_overlay
            optimized_text = await optimize_badge_text({
                "badge_name": validated.badge_name,
                "badge_description": validated.badge_description,
                "institution": request.institution or ""
            })

            image_base64, image_config = await generate_badge_with_text(
                short_title=optimized_text.get("short_title", validated.badge_name),
                institute=optimized_text.get("institution_display", request.institution or ""),
                achievement_phrase=optimized_text.get("achievement_phrase", "Achievement Unlocked")
            )

        # Generate badge ID
        badge_id = str(uuid.uuid4())

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
        regeneration_map = {param: "true" for param in request.regenerate_parameters}
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

            # Extract icon name from suggestions
            icon_name = icon_suggestions.get('suggested_icon', {}).get('name', 'trophy.png')

            image_base64, image_config = await generate_badge_with_icon(
                icon_name=icon_name
            )

        else:  # text_overlay
            optimized_text = await optimize_badge_text({
                "badge_name": validated.badge_name,
                "badge_description": validated.badge_description,
                "institution": request.institution or ""
            })

            image_base64, image_config = await generate_badge_with_text(
                short_title=optimized_text.get("short_title", validated.badge_name),
                institute=optimized_text.get("institution_display", request.institution or ""),
                achievement_phrase=optimized_text.get("achievement_phrase", "Achievement Unlocked")
            )

        # Generate badge ID
        badge_id = str(uuid.uuid4())

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

# Helper functions for streaming
def format_streaming_response(data: Dict[str, Any]) -> str:
    """Format data for streaming response"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

def create_streaming_response(generator):
    """Create a streaming response with proper headers"""
    return StreamingResponse(
        generator,
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/plain; charset=utf-8",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

# Normalize model JSON to our schema expectations
def _normalize_badge_json(badge_json: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(badge_json, dict):
        return {}
    # Ensure criteria is a dict with narrative
    criteria = badge_json.get("criteria")
    if isinstance(criteria, str):
        badge_json["criteria"] = {"narrative": criteria}
    elif isinstance(criteria, dict):
        # If narrative came as plain string under a different key, keep as is; no-op
        pass
    else:
        # Default empty structure
        badge_json["criteria"] = {"narrative": ""}
    return badge_json

@router.post("/generate-badge-suggestions/stream")
async def generate_badge_stream(request: BadgeRequest):
    """Generate badge suggestions with streaming response"""
    start_time = time.time()
    request_id = None
    badge_id = str(uuid.uuid4())
    
    try:
        current_params = get_random_parameters(request)
        
        from app.services.text_processor import process_course_input
        processed_content = process_course_input(request.course_input)
        
        # Build user content - Modelfile handles system instructions
        user_content = f"""Course Content: {processed_content}

Parameters:
- Style: {settings.STYLE_DESCRIPTIONS.get(current_params['badge_style'])}
- Tone: {settings.TONE_DESCRIPTIONS.get(current_params['badge_tone'])}
- Level: {settings.LEVEL_DESCRIPTIONS.get(current_params['badge_level'])}
- Criterion Style: {settings.CRITERION_TEMPLATES.get(current_params['criterion_style'])}"""

        if request.institution:
            user_content += f"\n- Institution: {request.institution}"
        
        if request.custom_instructions:
            user_content += f"\n- Special Instructions: {request.custom_instructions}"

        user_content += '\n\nGenerate badge JSON with exact schema {"badge_name": "string", "badge_description": "string", "criteria": {"narrative": "string"}}:'

        # Minimal prompt - Modelfile handles all complex instructions
        prompt = user_content
        
        
        # Import ollama service
        from app.services.ollama_client import ollama_client
        MODEL_CONFIG = settings.MODEL_CONFIG

        async def generate_stream_response():
            nonlocal request_id
            accumulated_text = ""
            
            try:
                # Call the service layer for streaming generation
                async for chunk in ollama_client.generate_stream(
                    content=prompt,
                    temperature=MODEL_CONFIG.get("temperature", 0.2),
                    max_tokens=MODEL_CONFIG.get("num_predict", 1024),
                    top_p=MODEL_CONFIG.get("top_p", 0.8),
                    top_k=MODEL_CONFIG.get("top_k", 30),
                    repeat_penalty=MODEL_CONFIG.get("repeat_penalty", 1.05)
                ):
                    # Track request ID for logging
                    if chunk.get("request_id") and not request_id:
                        request_id = chunk.get("request_id")
                    
                    # Handle different chunk types
                    if chunk.get("type") == "token":
                        # Stream individual tokens
                        accumulated_text += chunk.get("content", "")
                        formatted_chunk = format_streaming_response({
                            "type": "token",
                            "content": chunk.get("content", ""),
                            "accumulated": accumulated_text,
                            "badge_id": badge_id
                        })
                        yield formatted_chunk
                        
                    elif chunk.get("type") == "final":
                        # Process the final response with advanced features
                        try:
                            # Extract and parse JSON from the accumulated text
                            raw_response = accumulated_text
                            
                            # Try to extract JSON from the accumulated text
                            try:
                                # Look for JSON content between ```json and ```
                                json_start = raw_response.find('```json')
                                json_end = raw_response.find('```', json_start + 7)
                                
                                if json_start != -1 and json_end != -1:
                                    json_content = raw_response[json_start + 7:json_end].strip()
                                    badge_json = json.loads(json_content)
                                else:
                                    # Fallback: try to extract JSON from the full response
                                    badge_json = extract_json_from_response(raw_response)
                                
                                raw_model_output_str = raw_response
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse JSON from accumulated text: {e}")
                                error_chunk = {
                                    "type": "error",
                                    "content": f"Failed to parse JSON from response: {str(e)}",
                                    "badge_id": badge_id
                                }
                                yield format_streaming_response(error_chunk)
                                return
                            
                            badge_json = _normalize_badge_json(badge_json)
                            badge_json["selected_parameters"] = current_params
                            badge_json["processed_course_input"] = processed_content

                            # Validate badge data
                            try:
                                validated = BadgeValidated(
                                    badge_name=badge_json.get("badge_name", ""),
                                    badge_description=badge_json.get("badge_description", ""),
                                    criteria=badge_json.get("criteria", {}),
                                    raw_model_output=raw_model_output_str
                                )
                            except ValidationError as ve:
                                logger.warning("Badge validation failed: %s", ve)
                                error_chunk = {
                                    "type": "error",
                                    "content": f"Badge schema validation error: {ve}",
                                    "badge_id": badge_id
                                }
                                yield format_streaming_response(error_chunk)
                                return

                            # Scrape institution colors if URL provided
                            institution_colors = None
                            if request.institute_url:
                                try:
                                    from app.services.web_color_scraper import scrape_institution_colors_async
                                    institution_colors = await scrape_institution_colors_async(request.institute_url)
                                    logger.info(f"Scraped colors from {request.institute_url}: {institution_colors}")
                                except Exception as color_error:
                                    logger.warning(f"Failed to scrape colors from {request.institute_url}: {color_error}")

                            # Generate image configuration with random selection
                            image_type = random.choice(["text_overlay", "icon_based"])
                            logger.info(f"Selected image type: {image_type}")

                            if image_type == "icon_based":
                                icon_suggestions_result = await get_icon_suggestions_for_badge(
                                    badge_name=validated.badge_name,
                                    badge_description=validated.badge_description,
                                    custom_instructions=request.custom_instructions or "",
                                    top_k=3
                                )

                                # Extract icon name from suggestions
                                icon_name = icon_suggestions_result.get('suggested_icon', {}).get('name', 'trophy.png')

                                image_base64, image_config = await generate_badge_with_icon(
                                    icon_name=icon_name,
                                    colors=institution_colors
                                )

                            else:  # text_overlay
                                optimized_text = await optimize_badge_text({
                                    "badge_name": validated.badge_name,
                                    "badge_description": validated.badge_description,
                                    "institution": request.institution or ""
                                })

                                image_base64, image_config = await generate_badge_with_text(
                                    short_title=optimized_text.get("short_title", validated.badge_name),
                                    institute=optimized_text.get("institution_display", request.institution or ""),
                                    achievement_phrase=optimized_text.get("achievement_phrase", "Achievement Unlocked"),
                                    colors=institution_colors
                                )
                            # Log image generation summary (do not log full base64)
                            try:
                                preview = (image_base64 or "")[:48]
                                logger.info(
                                    "Badge image generated | base64_len=%s preview=%s...",
                                    len(image_base64) if isinstance(image_base64, str) else 0,
                                    preview
                                )
                            except Exception:
                                pass

                            # Transform to new JSON schema format
                            result = BadgeResponse(
                                credentialSubject={
                                    "achievement": {
                                        "criteria": validated.criteria,
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

                            # Store in history
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
                                "result": result,
                                "generation_time": time.time() - start_time
                            }
                            badge_history.append(history_entry)
                            
                            if len(badge_history) > 50:
                                badge_history.pop(0)

                            # Stream the final result
                            try:
                                # Convert result to dict safely
                                if hasattr(result, 'dict'):
                                    result_dict = result.dict()
                                elif hasattr(result, '__dict__'):
                                    result_dict = result.__dict__
                                else:
                                    result_dict = dict(result) if isinstance(result, dict) else {}
                                
                                final_chunk = {
                                    "type": "final",
                                    "content": result_dict,
                                    "badge_id": badge_id,
                                    "generation_time": time.time() - start_time
                                }
                                yield format_streaming_response(final_chunk)
                                
                            except Exception as dict_error:
                                logger.error(f"Error converting result to dict: {dict_error}")
                                # Fallback: create a simple response
                                fallback_result = {
                                    "credentialSubject": {
                                        "achievement": {
                                            "criteria": validated.criteria,
                                            "description": validated.badge_description,
                                            "image": {
                                                "id": f"https://example.com/achievements/badge_{badge_id}/image",
                                                "image_base64": None
                                            },
                                            "name": validated.badge_name
                                        }
                                    },
                                    "badge_id": badge_id
                                }
                                
                                final_chunk = {
                                    "type": "final",
                                    "content": fallback_result,
                                    "badge_id": badge_id,
                                    "generation_time": time.time() - start_time
                                }
                                yield format_streaming_response(final_chunk)
                            
                            selected_params = badge_json.get("selected_parameters", {})
                            logger.info(f"Generated badge ID {badge_id}: '{validated.badge_name}' with parameters: {selected_params}")
                            
                        except Exception as e:
                            logger.error(f"Error processing final response: {e}", exc_info=True)
                            error_chunk = {
                                "type": "error",
                                "content": f"Error processing final response: {str(e)}",
                                "badge_id": badge_id,
                                "error_details": str(e)
                            }
                            yield format_streaming_response(error_chunk)
                            
                    elif chunk.get("type") == "error":
                        # Stream error chunks
                        yield format_streaming_response(chunk)
                
                # Log successful completion
                log_response("Streaming badge suggestions generation", True, request_id)
                
            except Exception as e:
                # Handle streaming errors
                error_chunk = {
                    "type": "error",
                    "content": f"Streaming generation failed: {str(e)}",
                    "request_id": request_id,
                    "badge_id": badge_id
                }
                yield format_streaming_response(error_chunk)
                log_response("Streaming badge suggestions generation", False, request_id)
        
        # Create streaming response
        return create_streaming_response(generate_stream_response())
        
    except ValueError as e:
        # Handle validation errors
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
        
    except Exception as e:
        # Handle other errors
        log_response("Streaming badge suggestions generation", False, request_id)
        raise handle_error(e, "Streaming badge suggestions generation", request_id)
    
class BadgeRegenerateRequest(BaseModel):
    """Request model for badge regeneration using custom instructions"""
    custom_instructions: str  # e.g., "give badge name", "make it more concise", "focus on leadership"
    institution: Optional[str] = None  # Optional: override institution from last badge

    
@router.post("/regenerate-badge-stream")
async def regenerate_badge_stream(request: BadgeRegenerateRequest):
    """Regenerate badge using custom instructions and automatically retrieved context"""
    start_time = time.time()
    request_id = None
    badge_id = str(uuid.uuid4())
    
    try:
        # Get the last badge from history automatically
        if not badge_history:
            raise ValueError("No previous badge found in history. Please generate a badge first.")
        
        last_badge_entry = badge_history[-1]
        
        # Extract previous badge data and course input from history
        previous_badge = last_badge_entry.get("result")
        course_input = last_badge_entry.get("course_input", "")
        processed_content = last_badge_entry.get("processed_course_input", course_input)
        
        # Get current parameters from previous badge
        current_params = last_badge_entry.get("selected_parameters", {})
        
        # Extract previous badge achievement data
        if hasattr(previous_badge, 'dict'):
            previous_badge_dict = previous_badge.dict()
        elif hasattr(previous_badge, '__dict__'):
            previous_badge_dict = previous_badge.__dict__
        else:
            previous_badge_dict = previous_badge
            
        previous_achievement = previous_badge_dict.get('credentialSubject', {}).get('achievement', {})
        
        # Build context with previous badge data
        previous_badge_context = f"""Previous Badge Data:
- Badge Name: {previous_achievement.get('name', 'N/A')}
- Badge Description: {previous_achievement.get('description', 'N/A')}
- Criteria: {json.dumps(previous_achievement.get('criteria', {}), indent=2)}"""
        
        # Build user content with custom instructions
        user_content = f"""Course Content: {processed_content}

{previous_badge_context}

Custom Instructions: {request.custom_instructions}

Parameters:
- Style: {settings.STYLE_DESCRIPTIONS.get(current_params.get('badge_style', 'professional'))}
- Tone: {settings.TONE_DESCRIPTIONS.get(current_params.get('badge_tone', 'formal'))}
- Level: {settings.LEVEL_DESCRIPTIONS.get(current_params.get('badge_level', 'intermediate'))}
- Criterion Style: {settings.CRITERION_TEMPLATES.get(current_params.get('criterion_style', 'descriptive'))}"""

        institution = last_badge_entry.get("institution") or request.institution
        if institution:
            user_content += f"\n- Institution: {institution}"

        user_content += '\n\nBased on the custom instructions above, regenerate the badge. Keep fields unchanged if not mentioned in the instructions. Generate JSON with exact schema {"badge_name": "string", "badge_description": "string", "criteria": {"narrative": "string"}}:'

        prompt = user_content
        
        # Import ollama service
        from app.services.ollama_client import ollama_client
        MODEL_CONFIG = settings.MODEL_CONFIG

        async def generate_stream_response():
            nonlocal request_id
            accumulated_text = ""
            
            try:
                # Call the service layer for streaming generation
                async for chunk in ollama_client.generate_stream(
                    content=prompt,
                    temperature=MODEL_CONFIG.get("temperature", 0.15),
                    max_tokens=MODEL_CONFIG.get("num_predict", 400),
                    top_p=MODEL_CONFIG.get("top_p", 0.8),
                    top_k=MODEL_CONFIG.get("top_k", 30),
                    repeat_penalty=MODEL_CONFIG.get("repeat_penalty", 1.05)
                ):
                    # Track request ID for logging
                    if chunk.get("request_id") and not request_id:
                        request_id = chunk.get("request_id")
                    
                    # Handle different chunk types
                    if chunk.get("type") == "token":
                        # Stream individual tokens
                        accumulated_text += chunk.get("content", "")
                        formatted_chunk = format_streaming_response({
                            "type": "token",
                            "content": chunk.get("content", ""),
                            "accumulated": accumulated_text,
                            "badge_id": badge_id
                        })
                        yield formatted_chunk
                        
                    elif chunk.get("type") == "final":
                        # Process the final response with selective field update
                        try:
                            # Extract and parse JSON from the accumulated text
                            raw_response = accumulated_text
                            
                            # Try to extract JSON from the accumulated text
                            try:
                                # Look for JSON content between ```json and ```
                                json_start = raw_response.find('```json')
                                json_end = raw_response.find('```', json_start + 7)
                                
                                if json_start != -1 and json_end != -1:
                                    json_content = raw_response[json_start + 7:json_end].strip()
                                    regenerated_json = json.loads(json_content)
                                else:
                                    # Fallback: try to extract JSON from the full response
                                    regenerated_json = extract_json_from_response(raw_response)
                                
                                raw_model_output_str = raw_response
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse JSON from accumulated text: {e}")
                                error_chunk = {
                                    "type": "error",
                                    "content": f"Failed to parse JSON from response: {str(e)}",
                                    "badge_id": badge_id
                                }
                                yield format_streaming_response(error_chunk)
                                return
                            
                            # Normalize regenerated JSON
                            regenerated_json = _normalize_badge_json(regenerated_json)
                            
                            # Use regenerated data directly
                            regenerated_json["selected_parameters"] = current_params
                            regenerated_json["processed_course_input"] = processed_content

                            # Validate regenerated badge data
                            try:
                                validated = BadgeValidated(
                                    badge_name=regenerated_json.get("badge_name", ""),
                                    badge_description=regenerated_json.get("badge_description", ""),
                                    criteria=regenerated_json.get("criteria", {}),
                                    raw_model_output=raw_model_output_str
                                )
                            except ValidationError as ve:
                                logger.warning("Badge validation failed: %s", ve)
                                error_chunk = {
                                    "type": "error",
                                    "content": f"Badge schema validation error: {ve}",
                                    "badge_id": badge_id
                                }
                                yield format_streaming_response(error_chunk)
                                return

                            # Always regenerate image for regenerated badges
                            image_type = random.choice(["text_overlay", "icon_based"])
                            logger.info(f"Regenerating badge with image type: {image_type}")

                            if image_type == "icon_based":
                                icon_suggestions_result = await get_icon_suggestions_for_badge(
                                    badge_name=validated.badge_name,
                                    badge_description=validated.badge_description,
                                    custom_instructions=request.custom_instructions or "",
                                    top_k=3
                                )

                                # Extract icon name from suggestions
                                icon_name = icon_suggestions_result.get('suggested_icon', {}).get('name', 'trophy.png')

                                image_base64, image_config = await generate_badge_with_icon(
                                    icon_name=icon_name
                                )

                            else:  # text_overlay
                                optimized_text = await optimize_badge_text({
                                    "badge_name": validated.badge_name,
                                    "badge_description": validated.badge_description,
                                    "institution": institution or ""
                                })

                                image_base64, image_config = await generate_badge_with_text(
                                    short_title=optimized_text.get("short_title", validated.badge_name),
                                    institute=optimized_text.get("institution_display", institution or ""),
                                    achievement_phrase=optimized_text.get("achievement_phrase", "Achievement Unlocked")
                                )
                            logger.info(f"Image regenerated | base64_len={len(image_base64) if isinstance(image_base64, str) else 0}")

                            # Transform to new JSON schema format
                            result = BadgeResponse(
                                credentialSubject={
                                    "achievement": {
                                        "criteria": validated.criteria,
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

                            # Store in history
                            history_entry = {
                                "id": len(badge_history) + 1,
                                "timestamp": datetime.now().isoformat(),
                                "course_input": course_input,
                                "processed_course_input": regenerated_json.get("processed_course_input", processed_content),
                                "regeneration_type": "custom_instruction",
                                "custom_instructions": request.custom_instructions,
                                "institution": institution,
                                "selected_image_type": image_type,
                                "selected_parameters": regenerated_json.get("selected_parameters", {}),
                                "badge_id": badge_id,
                                "result": result,
                                "generation_time": time.time() - start_time
                            }
                            badge_history.append(history_entry)
                            
                            if len(badge_history) > 50:
                                badge_history.pop(0)

                            # Stream the final result
                            try:
                                # Convert result to dict safely
                                if hasattr(result, 'dict'):
                                    result_dict = result.dict()
                                elif hasattr(result, '__dict__'):
                                    result_dict = result.__dict__
                                else:
                                    result_dict = dict(result) if isinstance(result, dict) else {}
                                
                                final_chunk = {
                                    "type": "final",
                                    "content": result_dict,
                                    "badge_id": badge_id,
                                    "generation_time": time.time() - start_time
                                }
                                yield format_streaming_response(final_chunk)
                                
                            except Exception as dict_error:
                                logger.error(f"Error converting result to dict: {dict_error}")
                                # Fallback: create a simple response
                                fallback_result = {
                                    "credentialSubject": {
                                        "achievement": {
                                            "criteria": validated.criteria,
                                            "description": validated.badge_description,
                                            "image": {
                                                "id": f"https://example.com/achievements/badge_{badge_id}/image",
                                                "image_base64": image_base64
                                            },
                                            "name": validated.badge_name
                                        }
                                    },
                                    "badge_id": badge_id
                                }
                                
                                final_chunk = {
                                    "type": "final",
                                    "content": fallback_result,
                                    "badge_id": badge_id,
                                    "generation_time": time.time() - start_time
                                }
                                yield format_streaming_response(final_chunk)
                            
                            logger.info(f"Regenerated badge ID {badge_id}: '{validated.badge_name}'")
                            
                        except Exception as e:
                            logger.error(f"Error processing final response: {e}", exc_info=True)
                            error_chunk = {
                                "type": "error",
                                "content": f"Error processing final response: {str(e)}",
                                "badge_id": badge_id,
                                "error_details": str(e)
                            }
                            yield format_streaming_response(error_chunk)
                            
                    elif chunk.get("type") == "error":
                        # Stream error chunks
                        yield format_streaming_response(chunk)
                
                # Log successful completion
                log_response("Streaming badge regeneration", True, request_id)
                
            except Exception as e:
                # Handle streaming errors
                error_chunk = {
                    "type": "error",
                    "content": f"Streaming regeneration failed: {str(e)}",
                    "request_id": request_id,
                    "badge_id": badge_id
                }
                yield format_streaming_response(error_chunk)
                log_response("Streaming badge regeneration", False, request_id)
        
        # Create streaming response
        return create_streaming_response(generate_stream_response())
        
    except ValueError as e:
        # Handle validation errors
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
        
    except Exception as e:
        # Handle other errors
        log_response("Streaming badge regeneration", False, request_id)
        raise handle_error(e, "Streaming badge regeneration", request_id)

def get_badge_from_history(badge_id: str) -> Dict[str, Any]:
    """Retrieve badge from history by badge_id"""
    for entry in badge_history:
        if entry.get("badge_id") == badge_id:
            return entry
    raise HTTPException(status_code=404, detail=f"Badge with ID {badge_id} not found")

def build_field_specific_prompt(field: str, original_badge: Dict[str, Any], custom_instructions: Optional[str] = None) -> str:
    """Build a focused prompt for regenerating a specific field"""

    # Extract current badge data
    result = original_badge.get("result", {})
    if hasattr(result, 'dict'):
        result_dict = result.dict()
    elif hasattr(result, '__dict__'):
        result_dict = result.__dict__
    else:
        result_dict = result

    achievement = result_dict.get("credentialSubject", {}).get("achievement", {})
    current_title = achievement.get("name", "")
    current_description = achievement.get("description", "")
    current_criteria = achievement.get("criteria", {})

    course_input = original_badge.get("course_input", "")

    # Field-specific prompts
    field_prompts = {
        "title": "Generate ONLY a new, concise badge title/name. Keep it under 50 characters.",
        "description": "Generate ONLY a new badge description. Make it clear and comprehensive.",
        "criteria": "Generate ONLY new achievement criteria text. Focus on what learners must demonstrate."
    }

    # Build context
    context = f"""Current Badge:
- Title: {current_title}
- Description: {current_description}
- Criteria: {current_criteria.get('narrative', '') if isinstance(current_criteria, dict) else current_criteria}

Original Course Content: {course_input}

Task: {field_prompts[field]}"""

    if custom_instructions:
        context += f"\nAdditional Instructions: {custom_instructions}"

    context += f"\n\nRespond with ONLY the new {field} text, no JSON, no formatting, just the raw text:"

    return context

def merge_field_update(original_badge: Dict[str, Any], field: str, new_value: str) -> BadgeResponse:
    """Create updated badge with only the specified field changed"""

    # Extract original badge data
    result = original_badge.get("result", {})
    if hasattr(result, 'dict'):
        result_dict = result.dict()
    elif hasattr(result, '__dict__'):
        result_dict = result.__dict__
    else:
        result_dict = result

    # Create new badge with updated field
    achievement = result_dict.get("credentialSubject", {}).get("achievement", {})

    if field == "title":
        achievement["name"] = new_value.strip()
    elif field == "description":
        achievement["description"] = new_value.strip()
    elif field == "criteria":
        achievement["criteria"] = {"narrative": new_value.strip()}

    # Generate new badge ID
    new_badge_id = str(uuid.uuid4())

    # Create updated response
    updated_badge = BadgeResponse(
        credentialSubject={
            "achievement": achievement
        },
        badge_id=new_badge_id
    )

    return updated_badge

@router.post("/regenerate-field", response_model=BadgeResponse)
async def regenerate_field(request: FieldRegenerateRequest):
    """Regenerate a specific field of an existing badge"""
    start_time = time.time()

    try:
        # Get original badge from history
        original_badge = get_badge_from_history(request.badge_id)

        # Build field-specific prompt
        prompt = build_field_specific_prompt(
            field=request.field_to_change,
            original_badge=original_badge,
            custom_instructions=request.custom_instructions
        )

        # Import ollama service
        from app.services.ollama_client import ollama_client
        MODEL_CONFIG = settings.MODEL_CONFIG

        # Generate new field value
        new_value = ""
        async for chunk in ollama_client.generate_stream(
            content=prompt,
            temperature=MODEL_CONFIG.get("temperature", 0.15),
            max_tokens=200,  # Smaller for single field
            top_p=MODEL_CONFIG.get("top_p", 0.8),
            top_k=MODEL_CONFIG.get("top_k", 30),
            repeat_penalty=MODEL_CONFIG.get("repeat_penalty", 1.05)
        ):
            if chunk.get("type") == "token":
                new_value += chunk.get("content", "")
            elif chunk.get("type") == "final":
                break
            elif chunk.get("type") == "error":
                raise HTTPException(status_code=500, detail=f"Model error: {chunk.get('content')}")

        # Clean up the generated value
        new_value = new_value.strip()
        if not new_value:
            raise HTTPException(status_code=500, detail="Model generated empty response")

        # Create updated badge
        updated_badge = merge_field_update(
            original_badge=original_badge,
            field=request.field_to_change,
            new_value=new_value
        )

        # # Regenerate image if title or description changed
        # if request.field_to_change in ["title", "description"]:
        #     achievement = updated_badge.credentialSubject["achievement"]

        #     # Choose random image type
        #     image_type = random.choice(["text_overlay", "icon_based"])

        #     if image_type == "icon_based":
        #         icon_suggestions = await get_icon_suggestions_for_badge(
        #             badge_name=achievement["name"],
        #             badge_description=achievement["description"],
        #             custom_instructions=request.custom_instructions or "",
        #             top_k=3
        #         )

        #         image_config_wrapper = await generate_icon_image_config(
        #             achievement["name"],
        #             achievement["description"],
        #             icon_suggestions,
        #             request.institution or original_badge.get("institution", "")
        #         )

        #         image_config = image_config_wrapper.get("config", {})

        #     else:  # text_overlay
        #         optimized_text = await optimize_badge_text({
        #             "badge_name": achievement["name"],
        #             "badge_description": achievement["description"],
        #             "institution": request.institution or original_badge.get("institution", "")
        #         })

        #         image_config_wrapper = await generate_text_image_config(
        #             achievement["name"],
        #             achievement["description"],
        #             optimized_text,
        #             request.institution or original_badge.get("institution", "")
        #         )

        #         image_config = image_config_wrapper.get("config", {})

        #     # Generate new image
        #     image_base64 = await generate_badge_image(image_config)

        #     # Update badge with new image
        #     updated_badge.credentialSubject["achievement"]["image"] = {
        #         "id": f"https://example.com/achievements/badge_{updated_badge.badge_id}/image",
        #         "image_base64": image_base64
        #     }
        #     updated_badge.imageConfig = image_config

        # Store in history
        history_entry = {
            "id": len(badge_history) + 1,
            "timestamp": datetime.now().isoformat(),
            "parent_badge_id": request.badge_id,
            "field_changed": request.field_to_change,
            "change_type": "field_regeneration",
            "custom_instructions": request.custom_instructions,
            "institution": request.institution,
            "badge_id": updated_badge.badge_id,
            "result": updated_badge,
            "generation_time": time.time() - start_time
        }
        badge_history.append(history_entry)

        if len(badge_history) > 50:
            badge_history.pop(0)

        logger.info(f"Regenerated {request.field_to_change} for badge {updated_badge.badge_id}")
        return updated_badge

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /regenerate-field: %s", e)
        raise HTTPException(status_code=500, detail=f"Field regeneration error: {str(e)}")

