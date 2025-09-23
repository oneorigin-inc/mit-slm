"""
Badge controller functions for MCS architecture
"""
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from app.models.badge_model import (
    prepare_badge_suggestions_prompt, 
    get_random_badge_generation_config, 
    process_badge_generation_input, 
    extract_json_from_response,
    generate_icon_image_config,
    optimize_badge_text,
    generate_text_image_config,
    badge_history
)

from app.utils.controller_utils import get_icon_suggestions_for_badge
from app.models.schemas import GenerateRequest, GenerateResponse, BadgeValidated
from app.services.ollama_service import ollama_service
from app.utils.controller_utils import (
    handle_error,
    log_request,
    log_response,
    format_streaming_response,
    create_streaming_response
)
from app.utils.constants import MODEL_CONFIG
from app.core.logging_config import get_logger
import random
import json
import time
from datetime import datetime
from pydantic import ValidationError

logger = get_logger(__name__)


async def generate_badge_suggestions(request: GenerateRequest) -> GenerateResponse:
    """Generate badge suggestions from course content with advanced features"""
    start_time = time.time()
    request_id = None
    
    try:
        # Log the incoming request
        log_request("Badge suggestions generation", request.dict())
        
        # Process course input 
        processed_content = process_badge_generation_input(request.content)
        
        # Get random parameters if not provided 
        current_params = get_random_badge_generation_config(request)
        
        # Use provided parameters or fall back to random ones
        badge_style = request.badge_style or current_params["badge_style"]
        badge_tone = request.badge_tone or current_params["badge_tone"]
        criterion_style = request.criterion_style or current_params["criterion_style"]
        badge_level = request.badge_level or current_params["badge_level"]
        
        # Prepare the prompt using model functions
        prompt = prepare_badge_suggestions_prompt(
            content=processed_content,
            badge_style=badge_style,
            badge_tone=badge_tone,
            criterion_style=criterion_style,
            badge_level=badge_level,
            custom_instructions=request.custom_instructions,
            institution=request.institution,
        )
        
        # Call the service layer for generation
        result = await ollama_service.generate(
            content=prompt,
            temperature=MODEL_CONFIG.get("temperature", 0.15),
            max_tokens=MODEL_CONFIG.get("num_predict", 400),
            top_p=MODEL_CONFIG.get("top_p", 0.8),
            top_k=MODEL_CONFIG.get("top_k", 30),
            repeat_penalty=MODEL_CONFIG.get("repeat_penalty", 1.05)
        )
        
        # Extract and parse JSON from the response
        raw_response = result.get("response", "")
        
        # The response is already a parsed JSON object from the service
        if isinstance(raw_response, dict):
            badge_json = raw_response
            raw_model_output_str = json.dumps(raw_response, ensure_ascii=False)
        else:
            # Fallback: if it's a string, parse it
            badge_json = extract_json_from_response(raw_response)
            raw_model_output_str = raw_response if isinstance(raw_response, str) else str(raw_response or "")   
        badge_json["selected_parameters"] = current_params
        badge_json["processed_course_input"] = processed_content

        # Validate badge data
        try:
            validated = BadgeValidated(
                badge_name=badge_json.get("badge_name", ""),
                badge_description=badge_json.get("badge_description", ""),
                criteria=badge_json.get("criteria", {}),  # This already contains {"narrative": "string"}
                raw_model_output=raw_model_output_str
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
        badge_id = random.randint(100000, 999999)

        # Transform to new JSON schema format
        result = GenerateResponse(
            credentialSubject={
                "achievement": {
                    "criteria": validated.criteria,  # This is already {"narrative": "string"} format
                    "description": validated.badge_description,
                    "image": {
                        "id": f"https://example.com/achievements/badge_{badge_id}/image",
                        "image_base64": None  # Will be populated later when image is generated
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
            "course_input": (request.content[:100] + "...") if len(request.content) > 100 else request.content,
            "processed_course_input": badge_json.get("processed_course_input", request.content),
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
        
    except ValueError as e:
        # Handle validation errors
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
        
    except Exception as e:
        # Handle other errors
        log_response("Badge suggestions generation", False, request_id)
        raise handle_error(e, "Badge suggestions generation", request_id)


async def generate_badge_suggestions_stream(request: GenerateRequest) -> StreamingResponse:
    """Generate badge suggestions with streaming response and advanced features"""
    start_time = time.time()
    request_id = None
    
    try:
        # Log the incoming request
        log_request("Streaming badge suggestions generation", request.dict())
        
        # Process course input 
        processed_content = process_badge_generation_input(request.content)
        
        # Get random parameters if not provided
        current_params = get_random_badge_generation_config(request)
        
        # Use provided parameters or fall back to random ones
        badge_style = request.badge_style or current_params["badge_style"]
        badge_tone = request.badge_tone or current_params["badge_tone"]
        criterion_style = request.criterion_style or current_params["criterion_style"]
        badge_level = request.badge_level or current_params["badge_level"]
        
        # Prepare the prompt using model functions
        prompt = prepare_badge_suggestions_prompt(
            content=processed_content,
            badge_style=badge_style,
            badge_tone=badge_tone,
            criterion_style=criterion_style,
            badge_level=badge_level,
            custom_instructions=request.custom_instructions,
            institution=request.institution
        )
        
        # Generate badge ID
        badge_id = random.randint(100000, 999999)
        
        async def generate_stream_response():
            nonlocal request_id
            accumulated_text = ""
            
            try:
                # Call the service layer for streaming generation
                async for chunk in ollama_service.generate_stream(
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
                        # Process the final response with advanced features
                        try:
                            # Extract and parse JSON from the response
                            raw_response = chunk.get("content", "")
                            
                            # The response is already a parsed JSON object from the service
                            if isinstance(raw_response, dict):
                                badge_json = raw_response
                                raw_model_output_str = json.dumps(raw_response, ensure_ascii=False)
                            else:
                                # Fallback: if it's a string, parse it
                                badge_json = extract_json_from_response(raw_response)
                                raw_model_output_str = str(raw_response) if raw_response else ""
                            
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
                                
                                # Extract the suggested icon and alternatives
                                suggested_icon = icon_suggestions_result.get("suggested_icon", {})
                                alternatives = icon_suggestions_result.get("alternatives", [])
                                
                                # Convert to the format expected by generate_icon_image_config
                                icon_suggestions = [suggested_icon] + alternatives
                                
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

                            # Transform to new JSON schema format
                            result = GenerateResponse(
                                credentialSubject={
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
                                imageConfig=image_config,
                                badge_id=badge_id
                            )

                            # Store in history
                            history_entry = {
                                "id": len(badge_history) + 1,
                                "timestamp": datetime.now().isoformat(),
                                "course_input": (request.content[:100] + "...") if len(request.content) > 100 else request.content,
                                "processed_course_input": badge_json.get("processed_course_input", request.content),
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
                            final_chunk = {
                                "type": "final",
                                "content": result.dict(),
                                "badge_id": badge_id,
                                "generation_time": time.time() - start_time
                            }
                            yield format_streaming_response(final_chunk)
                            
                            selected_params = badge_json.get("selected_parameters", {})
                            logger.info(f"Generated badge ID {badge_id}: '{validated.badge_name}' with parameters: {selected_params}")
                            
                        except Exception as e:
                            logger.error(f"Error processing final response: {e}")
                            error_chunk = {
                                "type": "error",
                                "content": f"Error processing final response: {str(e)}",
                                "badge_id": badge_id
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


def _format_badge_response_github(badge_data: Dict[str, Any], badge_id: int, 
                                institution: Optional[str] = None) -> GenerateResponse:
    """Format badge generation response in GitHub version format"""
    try:
        # Create credentialSubject in Open Badges 3.0 format
        credential_subject = {
            "achievement": {
                "name": badge_data.get("badge_name", "Generated Badge"),
                "description": badge_data.get("badge_description", "A badge generated from course content"),
                "criteria": badge_data.get("criteria", {"narrative": "Complete the course requirements"}),
                "image": {
                    "id": f"https://example.com/achievements/badge_{badge_id}/image"
                }
            }
        }
        
        # Create basic image configuration
        image_config = {
            "type": "text_overlay",
            "badge_id": badge_id,
            "institution": institution or "Default Institution"
        }
        
        response = GenerateResponse(
            credentialSubject=credential_subject,
            imageConfig=image_config,
            badge_id=badge_id
        )
        
        logger.info(f"Formatted badge response with ID: {badge_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error formatting badge response: {e}")
        # Return a default response
        return GenerateResponse(
            credentialSubject={
                "achievement": {
                    "name": "Error Badge",
                    "description": "An error occurred while generating the badge",
                    "criteria": {"narrative": "Please try again"},
                    "image": {"id": "https://example.com/error.png"}
                }
            },
            imageConfig={"type": "error", "badge_id": badge_id},
            badge_id=badge_id
        )