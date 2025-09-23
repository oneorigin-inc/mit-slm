"""
Controllers package for MCS architecture - Function-based
"""
from .badge_controller import (
    generate_badge_suggestions,
    generate_badge_suggestions_stream
)
from .health_controller import health_check

__all__ = [
    "generate_badge_suggestions",
    "generate_badge_suggestions_stream",
    "health_check"
]
