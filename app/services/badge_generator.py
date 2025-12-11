import json
import re
import random
import logging
import sys
import os
from typing import Dict, Any, AsyncGenerator
from pydantic import ValidationError
from fastapi import HTTPException

from app.core.config import settings
from app.models.badge import BadgeValidated
from app.services.ollama_client import call_model_async, call_model_stream_async
from app.services.text_processor import process_course_input

# Add RAG retrieval import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from rag.retrieve_ob3 import retrieve_badge
from rag.update_vector_db import add_badge_to_vector_db

logger = logging.getLogger(__name__)

# Global embedding model for efficiency (loaded once, reused)
_embedding_model = None


def get_embedding_model():
    """Lazy-load and cache the embedding model"""
    global _embedding_model
    if _embedding_model is None:
        import torch
        from sentence_transformers import SentenceTransformer

        # Use GPU if enabled in settings and available, otherwise use CPU
        if settings.RAG_USE_GPU and torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"

        logger.info(f"Loading embedding model for vector DB updates on {device}...")
        _embedding_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2", device=device)
    return _embedding_model

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
    
    logger.warning("Could not extract valid JSON from response: %s", response_text[:5000])
    return {"error": "json_extraction_failed", "raw_response": response_text}

async def generate_badge_metadata_async(request) -> dict:
    """Generate badge metadata using RAG-enhanced few-shot prompting"""

    random_params = get_random_parameters(request)
    processed_course_input = process_course_input(request.course_input)

    # RAG retrieval: Get similar badges as examples
    retrieved_badges = retrieve_badge(processed_course_input, k=1)

    # Format as few-shot examples
    few_shot_examples = ""
    if retrieved_badges:
        few_shot_examples = "SIMILAR BADGE EXAMPLES (follow this format and quality):\n\n"
        for i, badge in enumerate(retrieved_badges, 1):
            # Escape any quotes in the badge data for valid JSON format
            badge_name = badge['badge_name'].replace('"', '\\"')
            badge_desc = badge['badge_description'].replace('"', '\\"')
            badge_crit = badge['criterion'].replace('"', '\\"')

            few_shot_examples += f"""Example {i} (Similarity Score: {badge['score']:.3f}):
{{
  "badge_name": "{badge_name}",
  "badge_description": "{badge_desc}",
  "criteria": {{
    "narrative": "{badge_crit}"
  }}
}}

"""

    # Build context-rich user message
    user_content = f"""{few_shot_examples}
NOW GENERATE A NEW BADGE FOR THIS COURSE:

Course Content: {processed_course_input}

Parameters:
- Style: {settings.STYLE_DESCRIPTIONS.get(random_params['badge_style'])}
- Tone: {settings.TONE_DESCRIPTIONS.get(random_params['badge_tone'])}
- Level: {settings.LEVEL_DESCRIPTIONS.get(random_params['badge_level'])}
- Criterion Style: {settings.CRITERION_TEMPLATES.get(random_params['criterion_style'])}"""

    if request.badge_style:
        user_content += f"\n- Badge Style: {request.badge_style} , incorporate prominently in both badge name and badge description"

    if request.institution:
        user_content += f"\n- Institution: {request.institution} , incorporate prominently in both badge name and badge description for branding"

    if request.custom_instructions:
        user_content += f"\n- Special Instructions: {request.custom_instructions}"

    user_content += """\n\nOUTPUT FORMAT: Return ONLY valid JSON in this exact format:
    {{
    "badge_name": "string",
    "badge_description": "string",
    "criteria": {{
        "narrative": "string"
    }}
   
}}
   """

   
    prompt = user_content
    
    response, metrics = await call_model_async(prompt)
    result = extract_json_from_response(response)

    # Add metrics and RAG info to result
    result['metrics'] = metrics
    result["raw_model_output"] = response
    result["selected_parameters"] = random_params
    result["processed_course_input"] = processed_course_input
    result["retrieved_examples"] = [
        {
            "badge_name": badge['badge_name'],
            "similarity_score": float(badge['score'])
        }
        for badge in retrieved_badges
    ]

    # Auto-update vector database with new badge (controlled by settings)
    if settings.AUTO_UPDATE_VECTOR_DB and result.get("badge_name") and result.get("badge_description"):
        try:
            model = get_embedding_model()
            badge_for_db = {
                "badge_name": result["badge_name"],
                "badge_description": result["badge_description"],
                "criteria": result.get("criteria", {}),
                "course_input": processed_course_input
            }
            success = add_badge_to_vector_db(badge_for_db, model=model)
            result["vector_db_updated"] = success
            if success:
                logger.info(f"Added new badge to vector DB: {result['badge_name']}")
        except Exception as e:
            logger.warning(f"Failed to update vector DB: {e}")
            result["vector_db_updated"] = False
    else:
        result["vector_db_updated"] = False if not settings.AUTO_UPDATE_VECTOR_DB else None

    return result


async def optimize_badge_text(badge_data: dict):
    """Optimize badge text for image overlay with strict word limits"""
    prompt = f"""Badge: "{badge_data['badge_name']}"
Description: "{badge_data['badge_description']}"

Generate optimized overlay text with STRICT WORD LIMITS:

CRITICAL REQUIREMENTS:
- short_title: MAXIMUM 2 WORDS (e.g., "Python Expert", "Data Analyst", "Cloud Architect")
- achievement_phrase: MAXIMUM 3 WORDS (e.g., "Master of Code", "Innovation Leader", "Problem Solver")

Guidelines:
- Use concise, impactful phrases
- Avoid articles (the, a, an) to save words
- Use powerful action words
- Make every word count

Examples:
GOOD:
  - short_title: "Python Expert" (2 words)
  - achievement_phrase: "Code with Confidence" (3 words)

BAD:
  - short_title: "Python Programming Specialist" (3 words - TOO LONG)
  - achievement_phrase: "Expert in Data Analysis" (4 words - TOO LONG)

Return JSON:
{{
    "short_title": "",
    "achievement_phrase": ""
}}"""

    response, metrics = await call_model_async(prompt)
    result = extract_json_from_response(response)
    result['metrics'] = metrics
    return result

async def generate_badge_metadata_stream_async(request) -> AsyncGenerator[Dict[str, Any], None]:
    """Generate badge metadata with streaming response using RAG-enhanced few-shot prompting"""

    # Process course input
    processed_input = process_course_input(request.course_input)

    # Get random parameters
    random_params = get_random_parameters(request)

    # RAG retrieval: Get similar badges as examples
    retrieved_badges = retrieve_badge(processed_input, k=2)

    # Format as few-shot examples
    few_shot_examples = ""
    if retrieved_badges:
        few_shot_examples = "SIMILAR BADGE EXAMPLES (follow this format and quality):\n\n"
        for i, badge in enumerate(retrieved_badges, 1):
            # Escape any quotes in the badge data for valid JSON format
            badge_name = badge['badge_name'].replace('"', '\\"')
            badge_desc = badge['badge_description'].replace('"', '\\"')
            badge_crit = badge['criterion'].replace('"', '\\"')

            few_shot_examples += f"""Example {i} (Similarity Score: {badge['score']:.3f}):
{{
  "badge_name": "{badge_name}",
  "badge_description": "{badge_desc}",
  "criteria": {{
    "narrative": "{badge_crit}"
  }}
}}

"""

    # Build the prompt
    prompt = f"""{few_shot_examples}
NOW GENERATE A NEW BADGE FOR THIS COURSE:

Generate Open Badges 3.0 compliant metadata from course content.

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
    }}
   
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
                badge_json["retrieved_examples"] = [
                    {
                        "badge_name": badge['badge_name'],
                        "similarity_score": float(badge['score'])
                    }
                    for badge in retrieved_badges
                ]

                # Auto-update vector database with new badge (controlled by settings)
                if settings.AUTO_UPDATE_VECTOR_DB and badge_json.get("badge_name") and badge_json.get("badge_description"):
                    try:
                        model = get_embedding_model()
                        badge_for_db = {
                            "badge_name": badge_json["badge_name"],
                            "badge_description": badge_json["badge_description"],
                            "criteria": badge_json.get("criteria", {}),
                            "course_input": processed_input
                        }
                        success = add_badge_to_vector_db(badge_for_db, model=model)
                        badge_json["vector_db_updated"] = success
                        if success:
                            logger.info(f"Added new badge to vector DB: {badge_json['badge_name']}")
                    except Exception as e:
                        logger.warning(f"Failed to update vector DB: {e}")
                        badge_json["vector_db_updated"] = False
                else:
                    badge_json["vector_db_updated"] = False if not settings.AUTO_UPDATE_VECTOR_DB else None

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

