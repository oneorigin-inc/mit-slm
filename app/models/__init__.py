"""
Models package for MCS architecture - Function-based
"""
from .schemas import GenerateRequest, GenerateResponse, HealthResponse, UsageInfo, BadgeValidated
from .badge_model import (
    prepare_badge_suggestions_prompt,
    validate_badge_data,
    clean_json_response,
    parse_response,
    format_badge_summary,
    get_badge_metadata,
    load_system_prompt,
    get_default_system_prompt,
    get_random_badge_generation_config,
    apply_regeneration_overrides,
    process_badge_generation_input,
    extract_key_concepts,
    calculate_similarity_scores,
    select_best_style_match,
    get_available_options,
    get_option_descriptions,
    extract_json_from_response,
    generate_icon_image_config,
    optimize_badge_text,
    generate_text_image_config,
    badge_history
)
from app.utils.controller_utils import get_icon_suggestions_for_badge
from .model_utils import (
    validate_model_data,
    convert_to_dict,
    sanitize_input,
    format_error_response,
    format_success_response
)
from app.utils.controller_utils import preprocess_text

__all__ = [
    "GenerateRequest",
    "GenerateResponse", 
    "HealthResponse",
    "UsageInfo",
    "BadgeValidated",
    "prepare_badge_suggestions_prompt",
    "validate_badge_data",
    "clean_json_response",
    "parse_response",
    "format_badge_summary",
    "get_badge_metadata",
    "load_system_prompt",
    "get_default_system_prompt",
    "get_random_badge_generation_config",
    "apply_regeneration_overrides",
    "process_badge_generation_input",
    "extract_key_concepts",
    "calculate_similarity_scores",
    "select_best_style_match",
    "get_available_options",
    "get_option_descriptions",
    "extract_json_from_response",
    "get_icon_suggestions_for_badge",
    "generate_icon_image_config",
    "optimize_badge_text",
    "generate_text_image_config",
    "badge_history",
    "preprocess_text",
    "validate_model_data",
    "convert_to_dict",
    "sanitize_input",
    "format_error_response",
    "format_success_response"
]