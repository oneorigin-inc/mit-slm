import json
import re
import random
import logging
from typing import Dict, Any
from pydantic import ValidationError
from fastapi import HTTPException

from app.core.config import settings
from app.models.badge import BadgeValidated
from app.services.ollama_client import call_model_async
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

    user_content += "\n\nGenerate badge JSON:"

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
- Brief description (1-2 lines)
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

