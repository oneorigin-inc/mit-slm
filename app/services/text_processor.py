import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# Text preprocessing setup
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer
    from nltk.tokenize import word_tokenize
    
    required_downloads = ['punkt', 'stopwords']
    
    for resource in required_downloads:
        try:
            nltk.data.find(f'tokenizers/{resource}' if 'punkt' in resource else f'corpora/{resource}')
        except LookupError:
            print(f"Downloading NLTK resource: {resource}")
            nltk.download(resource, quiet=True)
    
    NLTK_AVAILABLE = True
    STOP_WORDS = set(stopwords.words('english'))
    STEMMER = PorterStemmer()
    print("✓ NLTK initialized successfully")
    
except ImportError:
    NLTK_AVAILABLE = False
    STOP_WORDS = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'])
    print("⚠ NLTK not available, using basic preprocessing")

except Exception as e:
    print(f"⚠ NLTK setup failed: {e}, using basic preprocessing")
    NLTK_AVAILABLE = False
    STOP_WORDS = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'])

def preprocess_text(text: str) -> str:
    """Enhanced text preprocessing with improved handling."""
    if not text:
        return ""
    
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    if NLTK_AVAILABLE:
        try:
            tokens = word_tokenize(text)
            tokens = [STEMMER.stem(token) for token in tokens if token not in STOP_WORDS and len(token) > 2]
            return ' '.join(tokens)
        except Exception as e:
            logger.warning("NLTK preprocessing failed: %s", e)
    
    # Basic fallback preprocessing
    words = text.split()
    words = [word for word in words if word not in STOP_WORDS and len(word) > 2]
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

