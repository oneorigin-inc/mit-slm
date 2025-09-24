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
    """Generate badge metadata with random parameter selection"""
    
    # Get random parameters for empty fields
    random_params = get_random_parameters(request)
    
    # Process course input to handle multiple courses
    processed_course_input = process_course_input(request.course_input)
    
    style_desc = settings.STYLE_DESCRIPTIONS.get(random_params['badge_style'], "Use clear, comprehensive language with specific examples.")
    tone_desc = settings.TONE_DESCRIPTIONS.get(random_params['badge_tone'], "Professional and engaging tone.")
    level_desc = settings.LEVEL_DESCRIPTIONS.get(random_params['badge_level'], "Appropriate for learners with basic knowledge.")
    criterion_desc = settings.CRITERION_TEMPLATES.get(random_params['criterion_style'], "Clear, actionable criteria.")
    
    system_msg = "You are a badge metadata generator. Return only valid JSON with exact schema: {\"badge_name\": \"string\", \"badge_description\": \"string\", \"criteria\": {\"narrative\": \"string\"}}"
    
    user_content = f"""Create a unique badge for: {processed_course_input}

IMPORTANT: If this covers multiple courses or complex content, create a comprehensive badge name , description and criterion that encompasses all areas while maintaining focus and clarity.

Style: {style_desc}
Tone: {tone_desc}
Level: {level_desc}
Criterion Format: {criterion_desc}

Badge Name: Generate a creative and memorable name that captures the essence of the course(s). For multiple courses, create a unifying theme.
Badge Description: Provide a comprehensive description covering competencies mastered, technical tools, real-world applications, assessment rigor, employer value, and transferable skills. For multiple courses, integrate all subject areas cohesively.
Criteria: Focus on specific learning requirements, assessment methods, practical experiences, and evidence standards that span all course content."""

    user_content += f"\n\nTarget Level: {random_params['badge_level']} - {level_desc}"

    desc_instructions = "Badge description should cover: competencies mastered, technical tools, real-world applications, assessment rigor, employer value, transferable skills."
    
    if request.institution:
        desc_instructions += f" Highlight that this badge is issued by {request.institution} and emphasize the institution's credibility."
    user_content += f"\n\n{desc_instructions}"
        
    if request.custom_instructions:
        user_content += f" Additional focus: {request.custom_instructions}. follow the instructions and generate badge data accordingly"

    prompt = f"<|system|>{system_msg}<|end|>\n<|user|>{user_content}<|end|>\n<|assistant|>"
    
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

