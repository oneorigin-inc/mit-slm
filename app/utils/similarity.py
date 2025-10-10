import logging
import numpy as np
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


def calculate_batch_similarity(query: str, documents: List[str]) -> List[float]:
    """
    Calculate TF-IDF cosine similarity between query and multiple documents.
    
    Args:
        query: Search query text
        documents: List of document texts to compare against
        
    Returns:
        List of similarity scores (0.0 to 1.0) for each document
    """
    if not query or not documents:
        return [0.0] * len(documents)
    
    try:
        # Note: Documents should already be preprocessed by caller
        # Build shared vocabulary from all texts
        all_texts = [query] + documents
        
        # TF-IDF vectorizer with reasonable defaults
        vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),      # Unigrams and bigrams
            min_df=1,                 # Include all terms
            lowercase=False,          # Already lowercased in preprocessing
            token_pattern=r'\b\w+\b'  # Simple word tokenization
        )
        
        # Fit and transform all texts
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        
        # Query is first row, documents are remaining rows
        query_vector = tfidf_matrix[0:1]
        doc_vectors = tfidf_matrix[1:]
        
        # Calculate cosine similarities
        similarities = cosine_similarity(query_vector, doc_vectors)[0]
        
        return similarities.tolist()
        
    except Exception as e:
        logger.error(f"Batch similarity calculation failed: {e}", exc_info=True)
        return [0.0] * len(documents)


def calculate_similarity(query: str, document: str) -> float:
    """
    Calculate TF-IDF similarity between query and a single document.
    
    Args:
        query: Search query text
        document: Document text to compare against
        
    Returns:
        Similarity score (0.0 to 1.0)
    """
    scores = calculate_batch_similarity(query, [document])
    return scores[0] if scores else 0.0
