import json
import re
import random
import logging
from typing import Dict, Any, AsyncGenerator
from pydantic import ValidationError
from fastapi import HTTPException

from app.core.config import settings
from app.models.badge import BadgeValidated
from app.services.ollama_client import call_model_async, call_model_stream_async
from app.services.text_processor import process_course_input

logger = logging.getLogger(__name__)

def get_random_parameters(user_request) -> Dict[str, str]:
    """Generate random parameters, but respect user-provided ones"""
    
    # Get random selections for empty/default parameters
    random_params = {}
    
    # Badge Style - randomly select if not provided or empty
    if not user_request.badge_style or user_request.badge_style.strip() == "":
        random_params['badge_style'] = random.choice(list(settings.STYLE_DESCRIPTIONS.keys()))
    else:
        random_params['badge_style'] = user_request.badge_style
    
    # Badge Tone - randomly select if not provided or empty
    if not user_request.badge_tone or user_request.badge_tone.strip() == "":
        random_params['badge_tone'] = random.choice(list(settings.TONE_DESCRIPTIONS.keys()))
    else:
        random_params['badge_tone'] = user_request.badge_tone
    
    # Criterion Style - randomly select if not provided or empty
    if not user_request.criterion_style or user_request.criterion_style.strip() == "":
        random_params['criterion_style'] = random.choice(list(settings.CRITERION_TEMPLATES.keys()))
    else:
        random_params['criterion_style'] = user_request.criterion_style
    
    # Badge Level - randomly select if not provided or empty
    if not user_request.badge_level or user_request.badge_level.strip() == "":
        random_params['badge_level'] = random.choice(list(settings.LEVEL_DESCRIPTIONS.keys()))
    else:
        random_params['badge_level'] = user_request.badge_level
    
    return random_params

def apply_regeneration_overrides(current_params: Dict[str, str], regeneration_request: Dict[str, str]) -> Dict[str, str]:
    """Override specific parameters for regeneration"""
    updated_params = current_params.copy()
    
    # Override with new random selections for specified parameters
    if "badge_style" in regeneration_request:
        updated_params['badge_style'] = random.choice(list(settings.STYLE_DESCRIPTIONS.keys()))
    
    if "badge_tone" in regeneration_request:
        updated_params['badge_tone'] = random.choice(list(settings.TONE_DESCRIPTIONS.keys()))
    
    if "criterion_style" in regeneration_request:
        updated_params['criterion_style'] = random.choice(list(settings.CRITERION_TEMPLATES.keys()))
    
    if "badge_level" in regeneration_request:
        updated_params['badge_level'] = random.choice(list(settings.LEVEL_DESCRIPTIONS.keys()))
    
    return updated_params

def extract_json_from_response(response_text: str) -> dict:
    """Extract JSON from model response, handling various formats."""
    if not response_text or not response_text.strip():
        return {}
    
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON-like content
    json_patterns = [
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
        r'\{.*\}',
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, response_text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
    
    logger.warning("Could not extract valid JSON from response: %s", response_text[:200])
    return {"error": "json_extraction_failed", "raw_response": response_text}

async def generate_badge_metadata_async(request) -> dict:
    """Generate badge metadata using enhanced Modelfile system context"""
    
    random_params = get_random_parameters(request)
    processed_course_input = process_course_input(request.course_input)
    
    # Build context-rich user message
    user_content = f"""Course Content: {processed_course_input}

Parameters:
- Style: {settings.STYLE_DESCRIPTIONS.get(random_params['badge_style'])}
- Tone: {settings.TONE_DESCRIPTIONS.get(random_params['badge_tone'])}  
- Level: {settings.LEVEL_DESCRIPTIONS.get(random_params['badge_level'])}
- Criterion Style: {settings.CRITERION_TEMPLATES.get(random_params['criterion_style'])}"""

    if request.institution:
        user_content += f"\n- Institution: {request.institution}"
        
    if request.custom_instructions:
        user_content += f"\n- Special Instructions: {request.custom_instructions}"

    user_content += "\n\nGenerate badge JSON with exact schema {\"badge_name\": \"string\", \"badge_description\": \"string\", \"criteria\": {\"narrative\": \"string\"}}:"

    # Minimal prompt - Modelfile handles all the complex instructions
    prompt = user_content
    
    response = await call_model_async(prompt)
    result = extract_json_from_response(response)
    result["raw_model_output"] = response
    result["selected_parameters"] = random_params
    result["processed_course_input"] = processed_course_input
    
    return result


async def optimize_badge_text(badge_data: dict, max_title_chars: int = 25):
    """Optimize badge text for image overlay"""
    prompt = f"""Badge: "{badge_data['badge_name']}"
Description: "{badge_data['badge_description']}"
Institution: "{badge_data.get('institution', '')}"

Generate optimized text for image overlay:
- Short title (max {max_title_chars} chars)
- Brief description (25-30 characters max)
- Institution display name
- Key achievement phrase

Return JSON format:
{{
    "short_title": "condensed badge name",
    "brief_description": "one line summary",
    "institution_display": "institution name",
    "achievement_phrase": "motivational phrase"
}}"""

    response = await call_model_async(prompt)
    return extract_json_from_response(response)

async def generate_badge_metadata_stream_async(request) -> AsyncGenerator[Dict[str, Any], None]:
    """Generate badge metadata with streaming response using new format"""
    
    # Process course input
    processed_input = process_course_input(request.course_input)
    
    # Get random parameters
    random_params = get_random_parameters(request)
    
    # Build the prompt
    prompt = f"""Generate Open Badges 3.0 compliant metadata from course content.

COURSE CONTENT:
{processed_input}

BADGE STYLE: {random_params['badge_style']} - {settings.STYLE_DESCRIPTIONS[random_params['badge_style']]}
BADGE TONE: {random_params['badge_tone']} - {settings.TONE_DESCRIPTIONS[random_params['badge_tone']]}
BADGE LEVEL: {random_params['badge_level']} - {settings.LEVEL_DESCRIPTIONS[random_params['badge_level']]}
CRITERION STYLE: {random_params['criterion_style']} - {settings.CRITERION_TEMPLATES[random_params['criterion_style']]}

INSTITUTION: {request.institution or "Not specified"}
CUSTOM INSTRUCTIONS: {request.custom_instructions or "None"}

OUTPUT FORMAT: Return ONLY valid JSON in this exact format:
{{
    "badge_name": "string",
    "badge_description": "string", 
    "criteria": {{
        "narrative": "string"
    }},
    "raw_model_output": "string"
}}

Generate badge metadata now:"""

    # Stream the response using the new ollama service
    from app.services.ollama_client import ollama_client
    
    accumulated_text = ""
    async for chunk in ollama_client.generate_stream(
        content=prompt,
        temperature=settings.MODEL_CONFIG.get("temperature", 0.15),
        max_tokens=settings.MODEL_CONFIG.get("num_predict", 400),
        top_p=settings.MODEL_CONFIG.get("top_p", 0.8),
        top_k=settings.MODEL_CONFIG.get("top_k", 30),
        repeat_penalty=settings.MODEL_CONFIG.get("repeat_penalty", 1.05)
    ):
        if chunk.get("type") == "token":
            accumulated_text += chunk.get("content", "")
            yield chunk
        elif chunk.get("type") == "final":
            # Process the final response
            raw_response = chunk.get("content", "")
            
            # Try to extract JSON from the response
            try:
                badge_json = extract_json_from_response(raw_response)
                badge_json["selected_parameters"] = random_params
                badge_json["processed_course_input"] = processed_input
                
                # Return the parsed JSON as final content
                yield {
                    "type": "final",
                    "content": badge_json,
                    "request_id": chunk.get("request_id")
                }
            except Exception as e:
                logger.warning(f"Failed to parse JSON from streaming response: {e}")
                yield {
                    "type": "error",
                    "content": f"Failed to parse JSON: {str(e)}",
                    "request_id": chunk.get("request_id")
                }
        elif chunk.get("type") == "error":
            yield chunk

