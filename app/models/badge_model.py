"""
Badge model functions for MCS architecture
"""
import json
import re
import random
from typing import Dict, Any, Optional
from app.core.config import get_config
from app.core.logging_config import get_logger
from app.utils.constants import STYLE_DESCRIPTIONS, TONE_DESCRIPTIONS, LEVEL_DESCRIPTIONS, CRITERION_TEMPLATES, STOP_WORDS
from app.utils.constants import ICONS_DATA


logger = get_logger(__name__)
config = get_config()


def load_system_prompt() -> str:
    """Load system prompt from config file"""
    try:
        if config.SYSTEM_PROMPT_FILE.exists():
            with open(config.SYSTEM_PROMPT_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
        else:
            return get_default_system_prompt()
    except Exception as e:
        logger.error(f"Error loading system prompt: {e}")
        return get_default_system_prompt()


def get_default_system_prompt() -> str:
    """Get default system prompt"""
    return """Generate Open Badges 3.0 compliant metadata from course content with dynamic prompt adaptation.

DYNAMIC PROMPT SYSTEM: Adapt response based on user-specified options in the prompt:

STYLE ADAPTATIONS:
Professional: Use formal language, emphasize industry standards, focus on career advancement
Academic: Use scholarly language, emphasize learning outcomes, focus on educational rigor
Industry: Use sector-specific terminology, emphasize practical applications, focus on job readiness  
Technical: Use precise technical language, emphasize tools/technologies, focus on hands-on skills

COMPLEXITY ADAPTATIONS:
Beginner: Simple language, basic concepts, foundational skills
Intermediate: Moderate complexity, practical applications, skill building
Advanced: Complex concepts, expert-level knowledge, mastery indicators

DOMAIN ADAPTATIONS:
Business: Focus on business skills, management, entrepreneurship
Technology: Emphasize technical skills, programming, digital literacy
Healthcare: Highlight medical knowledge, patient care, clinical skills
Education: Focus on teaching methods, curriculum development, pedagogy

RESPONSE FORMAT: Always return valid JSON with this exact structure:
{
  "badge_name": "Descriptive badge name",
  "badge_description": "Comprehensive description of what the badge represents",
  "criteria": {
    "narrative": "Detailed criteria for earning this badge"
  },
  "tags": ["relevant", "tags", "for", "categorization"],
  "issuer": {
    "name": "Issuing Organization",
    "url": "https://organization.com"
  }
}

INSTRUCTIONS:
1. Analyze the course content thoroughly
2. Identify key learning outcomes and competencies
3. Create a badge that represents mastery of these competencies
4. Use appropriate style, complexity, and domain adaptations
5. Ensure the badge is meaningful and valuable
6. Return ONLY the JSON object, no additional text"""


def prepare_badge_suggestions_prompt(content: str, badge_style: str = "", badge_tone: str = "", 
                  criterion_style: str = "", badge_level: str = "", 
                  custom_instructions: str = None, institution: str = None) -> str:
    """Prepare the complete prompt for badge generation with advanced descriptions"""
    
    # Get descriptions from constants
    style_desc = STYLE_DESCRIPTIONS.get(badge_style, "Use clear, comprehensive language with specific examples.")
    tone_desc = TONE_DESCRIPTIONS.get(badge_tone, "Professional and engaging tone.")
    level_desc = LEVEL_DESCRIPTIONS.get(badge_level, "Appropriate for learners with basic knowledge.")
    criterion_desc = CRITERION_TEMPLATES.get(criterion_style, "Clear, actionable criteria.")
    
    # Process the content (like GitHub version)
    processed_course_input = process_badge_generation_input(content)
    
    # Detailed system message with JSON schema
    system_msg = "You are a badge metadata generator. Return only valid JSON with exact schema: {\"badge_name\": \"string\", \"badge_description\": \"string\", \"criteria\": {\"narrative\": \"string\"}}"
    
    # Comprehensive user content with detailed instructions
    user_content = f"""Create a unique badge for: {processed_course_input}

IMPORTANT: If this covers multiple courses or complex content, create a comprehensive badge name , description and criterion that encompasses all areas while maintaining focus and clarity.

Style: {style_desc}
Tone: {tone_desc}
Level: {level_desc}
Criterion Format: {criterion_desc}

Badge Name: Generate a creative and memorable name that captures the essence of the course(s). For multiple courses, create a unifying theme.
Badge Description: Provide a comprehensive description covering competencies mastered, technical tools, real-world applications, assessment rigor, employer value, and transferable skills. For multiple courses, integrate all subject areas cohesively.
Criteria: Focus on specific learning requirements, assessment methods, practical experiences, and evidence standards that span all course content."""

    # Add target level information
    user_content += f"\n\nTarget Level: {badge_level} - {level_desc}"

    # Add description instructions
    desc_instructions = "Badge description should cover: competencies mastered, technical tools, real-world applications, assessment rigor, employer value, transferable skills."
    
    if institution:
        desc_instructions += f" Highlight that this badge is issued by {institution} and emphasize the institution's credibility."
    user_content += f"\n\n{desc_instructions}"
        
    if custom_instructions:
        user_content += f" Additional focus: {custom_instructions}. follow the instructions and generate badge data accordingly"

    # Format the final prompt
    prompt = f"<|system|>{system_msg}<|end|>\n<|user|>{user_content}<|end|>\n<|assistant|>"
    
    return prompt


def validate_badge_data(badge_data: Dict[str, Any]) -> bool:
    """Validate badge data structure"""
    required_fields = ["badge_name", "badge_description", "criteria"]
    
    if not isinstance(badge_data, dict):
        return False
    
    for field in required_fields:
        if field not in badge_data:
            logger.warning(f"Missing required field: {field}")
            return False
    
    # Validate criteria structure
    if "criteria" in badge_data:
        criteria = badge_data["criteria"]
        if not isinstance(criteria, dict) or "narrative" not in criteria:
            logger.warning("Invalid criteria structure")
            return False
    
    return True


def clean_json_response(response_text: str) -> str:
    """Clean and extract JSON from AI response"""
    try:
        # Remove markdown code blocks
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)
        response_text = re.sub(r'`\s*', '', response_text)
        
        # Find JSON object boundaries
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx + 1]
            
            # Validate JSON
            json.loads(json_str)
            return json_str
        else:
            # If no JSON found, try to parse the whole response
            json.loads(response_text.strip())
            return response_text.strip()
            
    except json.JSONDecodeError:
        # If JSON parsing fails, return a default JSON structure
        logger.warning("Failed to parse JSON from response, returning default structure")
        return json.dumps({
            "error": "Failed to generate valid JSON",
            "raw_response": response_text[:200] + "..." if len(response_text) > 200 else response_text
        })


def parse_response(raw_response: str) -> Dict[str, Any]:
    """Parse and clean the AI response"""
    try:
        cleaned_response = clean_json_response(raw_response)
        parsed_response = json.loads(cleaned_response)
        
        # Validate the parsed response structure
        if not isinstance(parsed_response, dict):
            raise ValueError("Response must be a JSON object")
        
        # Ensure required fields exist
        if "badge_name" not in parsed_response:
            parsed_response["badge_name"] = "Generated Badge"
        
        if "badge_description" not in parsed_response:
            parsed_response["badge_description"] = "A badge generated from course content."
        
        if "criteria" not in parsed_response:
            parsed_response["criteria"] = {"narrative": "Complete the course requirements."}
        
        logger.info(f"Successfully parsed response with badge: {parsed_response.get('badge_name', 'Unknown')}")
        return parsed_response
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return {
            "error": "Failed to parse JSON response",
            "badge_name": "Error Badge",
            "badge_description": "An error occurred while generating the badge.",
            "criteria": {"narrative": "Please try again."}
        }
    except Exception as e:
        logger.error(f"Error parsing response: {e}")
        return {
            "error": f"Parsing error: {str(e)}",
            "badge_name": "Error Badge",
            "badge_description": "An error occurred while generating the badge.",
            "criteria": {"narrative": "Please try again."}
        }


def format_badge_summary(badge_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format a summary of the generated badge"""
    return {
        "badge_name": badge_data.get("badge_name", "Unknown Badge"),
        "description_length": len(badge_data.get("badge_description", "")),
        "criteria_length": len(badge_data.get("criteria", {}).get("narrative", "")),
        "has_criteria": "criteria" in badge_data and badge_data["criteria"],
        "word_count": len(badge_data.get("badge_description", "").split()),
        "is_valid": validate_badge_data(badge_data)
    }


def get_badge_metadata(badge_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata from badge data"""
    return {
        "name": badge_data.get("badge_name", ""),
        "description": badge_data.get("badge_description", ""),
        "criteria": badge_data.get("criteria", {}),
        "tags": badge_data.get("tags", []),
        "issuer": badge_data.get("issuer", {}),
        "created_at": badge_data.get("created_at"),
        "version": badge_data.get("version", "1.0")
    }


def get_random_badge_generation_config(request) -> Dict[str, Any]:
    """Generate random parameters for badge generation (like GitHub version)"""
  
    
    # Extract keys from constants
    badge_styles = list(STYLE_DESCRIPTIONS.keys())
    badge_tones = list(TONE_DESCRIPTIONS.keys())
    criterion_styles = list(CRITERION_TEMPLATES.keys())
    badge_levels = list(LEVEL_DESCRIPTIONS.keys())
    
    # Generate random parameters
    random_params = {
        "badge_style": random.choice(badge_styles),
        "badge_tone": random.choice(badge_tones),
        "criterion_style": random.choice(criterion_styles),
        "badge_level": random.choice(badge_levels)
    }
    
    return random_params


def apply_regeneration_overrides(current_params: Dict[str, Any], 
                               regeneration_map: Dict[str, bool]) -> Dict[str, Any]:
    """Apply regeneration overrides to current parameters"""
    updated_params = current_params.copy()
    
    # If regeneration is requested for a parameter, generate new random value
    if regeneration_map.get("badge_style", False):
        updated_params["badge_style"] = get_random_badge_generation_config({})["badge_style"]
    
    if regeneration_map.get("badge_tone", False):
        updated_params["badge_tone"] = get_random_badge_generation_config({})["badge_tone"]
    
    if regeneration_map.get("criterion_style", False):
        updated_params["criterion_style"] = get_random_badge_generation_config({})["criterion_style"]
    
    if regeneration_map.get("badge_level", False):
        updated_params["badge_level"] = get_random_badge_generation_config({})["badge_level"]
    
    return updated_params


def process_badge_generation_input(course_input: str) -> str:
    """Process and clean course input text (like GitHub version)"""
    if not course_input or not isinstance(course_input, str):
        return ""
    
    # Basic text cleaning
    processed = course_input.strip()
    
    # Remove excessive whitespace
    processed = re.sub(r'\s+', ' ', processed)
    
    # Remove special characters that might interfere with generation
    processed = re.sub(r'[^\w\s.,!?;:()-]', '', processed)
    
    # Ensure it's not too long (truncate if necessary)
    if len(processed) > 2000:
        processed = processed[:2000] + "..."
    
    return processed


def extract_key_concepts(text: str) -> list:
    """Extract key concepts from course text (simplified version)"""
    if not text:
        return []
    
    # Simple keyword extraction (without NLTK dependency)
    # Remove common stop words
    stop_words = STOP_WORDS
    
    # Extract words (simple approach)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Filter out stop words and get unique words
    concepts = list(set([word for word in words if word not in stop_words]))
    
    # Return top 10 most relevant concepts
    return concepts[:10]


def calculate_similarity_scores(concepts: list, style_descriptions: Dict[str, str] = None) -> Dict[str, float]:
    """Calculate similarity scores between concepts and style descriptions (simplified)"""
    if not concepts:
        return {}
    
    # Use constants if no style_descriptions provided
    if style_descriptions is None:
        style_descriptions = STYLE_DESCRIPTIONS
    
    similarity_scores = {}
    
    for style, description in style_descriptions.items():
        # Simple word overlap calculation
        description_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', description.lower()))
        concept_words = set(concepts)
        
        # Calculate Jaccard similarity
        intersection = len(concept_words.intersection(description_words))
        union = len(concept_words.union(description_words))
        
        similarity = intersection / union if union > 0 else 0
        similarity_scores[style] = similarity
    
    return similarity_scores


def select_best_style_match(similarity_scores: Dict[str, float]) -> str:
    """Select the best style match based on similarity scores"""
    if not similarity_scores:
        return "Professional"  # Default fallback
    
    # Return the style with highest similarity score
    best_style = max(similarity_scores, key=similarity_scores.get)
    return best_style


def get_available_options() -> Dict[str, list]:
    """Get all available options from constants"""
    return {
        "badge_styles": list(STYLE_DESCRIPTIONS.keys()),
        "badge_tones": list(TONE_DESCRIPTIONS.keys()),
        "criterion_styles": list(CRITERION_TEMPLATES.keys()),
        "badge_levels": list(LEVEL_DESCRIPTIONS.keys())
    }


def get_option_descriptions() -> Dict[str, Dict[str, str]]:
    """Get descriptions for all available options"""
    return {
        "badge_styles": STYLE_DESCRIPTIONS,
        "badge_tones": TONE_DESCRIPTIONS,
        "criterion_styles": CRITERION_TEMPLATES,
        "badge_levels": LEVEL_DESCRIPTIONS
    }


def extract_json_from_response(response_text: str) -> Dict[str, Any]:
    """Extract and parse JSON from response text"""
    if not response_text or not isinstance(response_text, str):
        return {}
    
    try:
        # First try to parse as-is
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    import re
    json_patterns = [
        r'```json\s*(\{.*?\})\s*```',  # ```json { ... } ```
        r'```\s*(\{.*?\})\s*```',      # ``` { ... } ```
        r'`(\{.*?\})`',                # `{ ... }`
        r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',  # General JSON object pattern
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
    
    # Try to find JSON object boundaries
    start_idx = response_text.find('{')
    end_idx = response_text.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = response_text[start_idx:end_idx + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # If all else fails, return empty dict
    logger.warning(f"Could not extract valid JSON from response: {response_text[:200]}...")
    return {}


# Global badge history storage
badge_history = []


# Icon suggestions function moved to app/utils/controller_utils.py


async def generate_icon_image_config(badge_name: str, badge_description: str, 
                                   icon_suggestions: list, institution: str = "") -> Dict[str, Any]:
    """Generate image configuration for icon-based badges"""
    if not icon_suggestions:
        return {"config": {}}
    
    # Handle both old and new format
    best_icon = icon_suggestions[0]
    if isinstance(best_icon, dict) and "icon" in best_icon:
        # Old format: {"icon": {...}, "score": ...}
        icon_data = best_icon["icon"]
    else:
        # New format: {"name": "...", "display_name": "...", ...}
        icon_data = best_icon
    
    config = {
        "type": "icon_based",
        "icon": {
            "name": icon_data.get("name", "trophy.png"),
            "display_name": icon_data.get("display_name", "Trophy"),
            "category": icon_data.get("category", "achievement")
        },
        "text": {
            "badge_name": badge_name,
            "institution": institution
        },
        "style": {
            "background_color": "#4A90E2",
            "text_color": "#FFFFFF",
            "icon_color": "#FFFFFF"
        },
        "layout": {
            "icon_position": "center",
            "text_position": "bottom"
        }
    }
    
    return {"config": config}


async def optimize_badge_text(badge_data: Dict[str, Any]) -> Dict[str, Any]:
    """Optimize badge text for better display"""
    badge_name = badge_data.get("badge_name", "")
    badge_description = badge_data.get("badge_description", "")
    institution = badge_data.get("institution", "")
    
    # Optimize badge name (truncate if too long)
    optimized_name = badge_name
    if len(optimized_name) > 30:
        optimized_name = optimized_name[:27] + "..."
    
    # Optimize description (truncate if too long)
    optimized_description = badge_description
    if len(optimized_description) > 100:
        optimized_description = optimized_description[:97] + "..."
    
    return {
        "optimized_name": optimized_name,
        "optimized_description": optimized_description,
        "institution": institution
    }


async def generate_text_image_config(badge_name: str, badge_description: str, 
                                   optimized_text: Dict[str, Any], institution: str = "") -> Dict[str, Any]:
    """Generate image configuration for text-overlay badges"""
    
    config = {
        "type": "text_overlay",
        "text": {
            "badge_name": optimized_text.get("optimized_name", badge_name),
            "badge_description": optimized_text.get("optimized_description", badge_description),
            "institution": institution
        },
        "style": {
            "background_color": "#2C3E50",
            "text_color": "#FFFFFF",
            "accent_color": "#3498DB"
        },
        "layout": {
            "text_alignment": "center",
            "font_size": "medium"
        }
    }
    
    return {"config": config}