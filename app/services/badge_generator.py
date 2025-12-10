import json
import re
import random
import logging
from typing import Dict, Any, AsyncGenerator

from app.core.config import settings
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

async def generate_badge_metadata_with_guidance_async(request) -> dict:
    """
    Generate badge metadata using guidance library for guaranteed structured JSON output.

    This method eliminates JSON parsing errors by using guidance's schema validation
    during generation, ensuring the output always conforms to the expected structure.
    """
    try:
        from app.services.guidance_badge_generator import guidance_generator

        random_params = get_random_parameters(request)
        processed_course_input = process_course_input(request.course_input)

        # Use guidance for structured generation with schema validation
        result = await guidance_generator.generate_badge_with_schema(
            course_content=processed_course_input,
            style=settings.STYLE_DESCRIPTIONS.get(random_params['badge_style'], ""),
            tone=settings.TONE_DESCRIPTIONS.get(random_params['badge_tone'], ""),
            level=settings.LEVEL_DESCRIPTIONS.get(random_params['badge_level'], ""),
            criterion_style=settings.CRITERION_TEMPLATES.get(random_params['criterion_style'], ""),
            institution=request.institution or "",
            custom_instructions=request.custom_instructions or ""
        )

        # Add metadata that the rest of the system expects
        result["selected_parameters"] = random_params
        result["processed_course_input"] = processed_course_input
        result["raw_model_output"] = json.dumps(result)  # For logging purposes

        logger.info(f"Generated badge with guidance: {result.get('badge_name', 'N/A')}")
        return result

    except Exception as e:
        logger.warning(f"Guidance generation failed, falling back to standard method: {e}")
        # Fallback to original method if guidance fails
        return await generate_badge_metadata_async_fallback(request)

async def generate_badge_metadata_async_fallback(request) -> dict:
    """
    Fallback method using the original regex-based JSON extraction.
    This is kept as a backup in case guidance generation fails.
    """
    random_params = get_random_parameters(request)
    processed_course_input = process_course_input(request.course_input)

    # Build context-rich user message
    user_content = f"""Course Content: {processed_course_input}

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

    user_content += "\n\nGenerate badge JSON with exact schema {\"badge_name\": \"string\", \"badge_description\": \"string\", \"criteria\": {\"narrative\": \"string\"}}:"

    # Minimal prompt - Modelfile handles all the complex instructions
    prompt = user_content

    response, metrics = await call_model_async(prompt)
    result = extract_json_from_response(response)

    # Add metrics to result
    result['metrics'] = metrics
    result["raw_model_output"] = response
    result["selected_parameters"] = random_params
    result["processed_course_input"] = processed_course_input

    return result

async def generate_badge_metadata_async(request) -> dict:
    """
    Generate badge metadata using enhanced Modelfile system context.

    Uses guidance for structured output if settings.USE_GUIDANCE=True, otherwise
    falls back to the original regex-based JSON extraction.
    """

    # Use guidance if enabled in settings
    if settings.USE_GUIDANCE:
        try:
            return await generate_badge_metadata_with_guidance_async(request)
        except Exception as e:
            logger.warning(f"Guidance method failed: {e}, using fallback")
            # Continue to fallback method

    # Fallback to original method
    return await generate_badge_metadata_async_fallback(request)


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
    """
    Generate badge metadata with streaming response.

    Uses guidance for validation if enabled, with automatic fallback to regex extraction.
    """

    # Use guidance streaming if enabled
    if settings.USE_GUIDANCE:
        try:
            async for chunk in _generate_badge_stream_with_guidance(request):
                yield chunk
            return
        except Exception as e:
            logger.warning(f"Guidance streaming failed: {e}, falling back to standard streaming")
            # Continue to fallback method

    # Fallback to original streaming method
    async for chunk in _generate_badge_stream_fallback(request):
        yield chunk


async def _generate_badge_stream_with_guidance(request) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Streaming generation with guidance validation.

    This streams tokens normally but validates/corrects the final output using guidance.
    """
    from app.services.ollama_client import ollama_client

    # Process course input
    processed_input = process_course_input(request.course_input)

    # Get random parameters
    random_params = get_random_parameters(request)

    # Build the prompt
    prompt = f"""Course Content: {processed_input}

Parameters:
- Style: {settings.STYLE_DESCRIPTIONS.get(random_params['badge_style'], "")}
- Tone: {settings.TONE_DESCRIPTIONS.get(random_params['badge_tone'], "")}
- Level: {settings.LEVEL_DESCRIPTIONS.get(random_params['badge_level'], "")}
- Criterion Style: {settings.CRITERION_TEMPLATES.get(random_params['criterion_style'], "")}"""

    if request.institution:
        prompt += f"\n- Institution: {request.institution}, Highlight institutional credibility and authority in badge name and badge description briefly."

    if request.custom_instructions:
        prompt += f"\n- Special Instructions: {request.custom_instructions}"

    prompt += '\n\nGenerate badge JSON with exact schema {"badge_name": "string", "badge_description": "string", "criteria": {"narrative": "string"}}:'

    accumulated_text = ""
    final_chunk_data = None

    # Stream tokens from Ollama
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
            final_chunk_data = chunk
            break
        elif chunk.get("type") == "error":
            yield chunk
            return

    # Validate/correct final output using guidance
    if final_chunk_data:
        try:
            # Try to extract JSON from streamed response
            initial_json = extract_json_from_response(accumulated_text)

            # If extraction succeeded and looks valid, use it
            if (initial_json and
                "badge_name" in initial_json and
                "badge_description" in initial_json and
                "criteria" in initial_json):

                badge_json = initial_json
                badge_json["selected_parameters"] = random_params
                badge_json["processed_course_input"] = processed_input

                yield {
                    "type": "final",
                    "content": badge_json,
                    "request_id": final_chunk_data.get("request_id"),
                    "metrics": final_chunk_data.get("metrics")
                }
            else:
                # Extraction failed, use guidance to regenerate proper structure
                logger.warning("Streaming JSON extraction failed, using guidance for validation")

                from app.services.guidance_badge_generator import guidance_generator

                corrected_result = await guidance_generator.generate_badge_with_schema(
                    course_content=processed_input,
                    style=settings.STYLE_DESCRIPTIONS.get(random_params['badge_style'], ""),
                    tone=settings.TONE_DESCRIPTIONS.get(random_params['badge_tone'], ""),
                    level=settings.LEVEL_DESCRIPTIONS.get(random_params['badge_level'], ""),
                    criterion_style=settings.CRITERION_TEMPLATES.get(random_params['criterion_style'], ""),
                    institution=request.institution or "",
                    custom_instructions=request.custom_instructions or ""
                )

                corrected_result["selected_parameters"] = random_params
                corrected_result["processed_course_input"] = processed_input

                yield {
                    "type": "final",
                    "content": corrected_result,
                    "request_id": final_chunk_data.get("request_id"),
                    "metrics": final_chunk_data.get("metrics"),
                    "guidance_corrected": True
                }

        except Exception as e:
            logger.error(f"Failed to process final streaming response: {e}")
            yield {
                "type": "error",
                "content": f"Failed to validate JSON: {str(e)}",
                "request_id": final_chunk_data.get("request_id")
            }


async def _generate_badge_stream_fallback(request) -> AsyncGenerator[Dict[str, Any], None]:
    """Original streaming implementation without guidance (fallback)"""

    from app.services.ollama_client import ollama_client

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

