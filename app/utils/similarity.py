import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.services.text_processor import preprocess_text
from typing import List  

logger = logging.getLogger(__name__)

def calculate_batch_similarity(query: str, documents: List[str]) -> List[float]:
    """Calculate TF-IDF similarity between query and multiple documents efficiently."""
    if not query or not documents:
        return [0.0] * len(documents)
    
    try:
        # Process all texts
        processed_query = preprocess_text(query)
        processed_docs = [preprocess_text(doc) for doc in documents]
        
        if not processed_query or not any(processed_docs):
            return [0.0] * len(documents)
        
        # Fit vectorizer on ALL documents together to build shared vocabulary
        all_texts = [processed_query] + processed_docs
        vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        
        # Compare query (index 0) against all documents (index 1+)
        query_vector = tfidf_matrix[0:1]
        doc_vectors = tfidf_matrix[1:]
        
        similarities = cosine_similarity(query_vector, doc_vectors)[0]
        
        return similarities.tolist()
        
    except Exception as e:
        logger.warning("Batch similarity calculation failed: %s", e)
        return [0.0] * len(documents)