import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.services.text_processor import preprocess_text

logger = logging.getLogger(__name__)

def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate TF-IDF cosine similarity between two texts."""
    if not text1 or not text2:
        return 0.0
    
    try:
        processed_text1 = preprocess_text(text1)
        processed_text2 = preprocess_text(text2)
        
        if not processed_text1 or not processed_text2:
            return 0.0
        
        vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform([processed_text1, processed_text2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        return float(similarity)
    except Exception as e:
        logger.warning("Similarity calculation failed: %s", e)
        return 0.0

