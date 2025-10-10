import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# Minimal stop words for basic filtering (optional)
BASIC_STOP_WORDS = set([
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
    'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'
])


def preprocess_text(text: str) -> str:
    """
    Minimal preprocessing optimized for TF-IDF similarity matching.
    
    NO stemming - preserves exact terms like "chemistry", "education"
    NO aggressive stop word removal - TF-IDF handles term importance
    
    Args:
        text: Input text to preprocess
        
    Returns:
        Preprocessed text with normalized whitespace and punctuation removed
    """
    if not text:
        return ""
    
    # Basic normalization
    text = text.lower().strip()
    
    # Remove punctuation but keep spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Only remove very short words (1-2 chars) that add no semantic value
    # Keep all meaningful words - let TF-IDF handle importance weighting
    words = text.split()
    words = [word for word in words if len(word) > 2]
    
    return ' '.join(words)


def preprocess_text_aggressive(text: str) -> str:
    """
    More aggressive preprocessing with stop word removal.
    Use this if you want cleaner text, but it may reduce match accuracy.
    
    Args:
        text: Input text to preprocess
        
    Returns:
        Preprocessed text with stop words removed
    """
    if not text:
        return ""
    
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    # Remove stop words but NO stemming
    words = text.split()
    words = [word for word in words if word not in BASIC_STOP_WORDS and len(word) > 2]
    
    return ' '.join(words)

def process_course_input(course_input: str) -> str:
    """Process course input to handle multiple courses or complex content"""
    
    # Check if it contains multiple courses (separated by common delimiters)
    course_separators = ['\n', ';', '|', '&', ' and ', ' + ', '//']
    
    # Count potential separators
    separator_found = None
    for sep in course_separators:
        if sep in course_input and course_input.count(sep) >= 1:
            separator_found = sep
            break
    
    if separator_found:
        courses = [course.strip() for course in course_input.split(separator_found) if course.strip()]
        if len(courses) > 1:
            return f"multiple courses: {', '.join(courses)}"
    
    return course_input

