"""
Reusable controller utility functions
"""
from typing import Any, Dict, Optional, List
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import json
import re
import logging
from app.core.logging_config import get_logger
from app.utils.constants import STOP_WORDS, ICONS_DATA, ICON_KEYWORDS

# Check if NLTK is available
try:
    import nltk
    from nltk.stem import PorterStemmer
    from nltk.tokenize import word_tokenize
    NLTK_AVAILABLE = True
    STEMMER = PorterStemmer()
except ImportError:
    NLTK_AVAILABLE = False
    STEMMER = None

# Check if sklearn is available
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = get_logger(__name__)


def handle_error(error: Exception, operation: str, request_id: Optional[int] = None) -> HTTPException:
    """Handle and log errors consistently"""
    error_message = f"{operation} failed: {str(error)}"
    
    if request_id:
        logger.error(f"Request #{request_id}: {error_message}")
    else:
        logger.error(error_message)
    
    return HTTPException(status_code=500, detail=error_message)


def log_request(operation: str, request_data: Dict[str, Any], request_id: Optional[int] = None):
    """Log incoming requests"""
    if request_id:
        logger.info(f"Request #{request_id}: {operation} - {summarize_request(request_data)}")
    else:
        logger.info(f"{operation} - {summarize_request(request_data)}")


def log_response(operation: str, success: bool, request_id: Optional[int] = None):
    """Log response completion"""
    status = "completed successfully" if success else "failed"
    if request_id:
        logger.info(f"Request #{request_id}: {operation} {status}")
    else:
        logger.info(f"{operation} {status}")


def summarize_request(request_data: Dict[str, Any]) -> str:
    """Create a summary of request data for logging"""
    summary_parts = []
    
    if "content" in request_data:
        content_length = len(str(request_data["content"]))
        summary_parts.append(f"content_length: {content_length}")
    
    if "temperature" in request_data:
        summary_parts.append(f"temperature: {request_data['temperature']}")
    
    if "max_tokens" in request_data:
        summary_parts.append(f"max_tokens: {request_data['max_tokens']}")
    
    return ", ".join(summary_parts) if summary_parts else "no parameters"


def format_streaming_response(chunk: Dict[str, Any]) -> str:
    """Format streaming response as Server-Sent Events"""
    try:
        data = json.dumps(chunk)
        return f"data: {data}\n\n"
    except Exception as e:
        logger.error(f"Error formatting streaming response: {e}")
        error_chunk = {
            "type": "error",
            "content": f"Error formatting response: {e}"
        }
        return f"data: {json.dumps(error_chunk)}\n\n"


def create_streaming_response(generator) -> StreamingResponse:
    """Create a streaming response with proper headers"""
    return StreamingResponse(
        generator,
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


def preprocess_text(text: str) -> str:
    """Enhanced text preprocessing with stemming and stopword removal."""
    if not text:
        return ""
    
    text = re.sub(r"[^\w\s]", " ", text.lower().strip())
    text = re.sub(r"\s+", " ", text)

    tokens: List[str]
    if NLTK_AVAILABLE:
        try:
            tokens = word_tokenize(text)
            tokens = [
                STEMMER.stem(token)
                for token in tokens
                if token not in STOP_WORDS and len(token) > 2
            ]
            return " ".join(tokens)
        except Exception as e:
            logger.warning("NLTK preprocessing failed: %s", e)

    # Fallback basic preprocessing
    tokens = [word for word in text.split() if word not in STOP_WORDS and len(word) > 2]
    return " ".join(tokens)


def calculate_similarity_batch(query: str, corpus: List[str]) -> List[float]:
    """Compute TF-IDF cosine similarity between query and multiple documents in one pass."""
    if not SKLEARN_AVAILABLE:
        logger.warning("sklearn not available, returning zero similarities")
        return [0.0] * len(corpus)
    
    try:
        processed_query = preprocess_text(query)
        processed_corpus = [preprocess_text(doc) for doc in corpus]

        all_docs = [processed_query] + processed_corpus
        vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform(all_docs)

        similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
        return similarities.tolist()
    except Exception as e:
        logger.warning("Batch similarity calculation failed: %s", e)
        return [0.0] * len(corpus)


async def get_icon_suggestions_for_badge(
    badge_name: str,
    badge_description: str,
    custom_instructions: str = "",
    top_k: int = 3
) -> Dict[str, Any]:
    """Get icon suggestions using TF-IDF similarity when ICONS_DATA is available, else keyword matching."""
    combined_text = f"{badge_name} {badge_description} {custom_instructions}".strip()

    # --- Case 1: TF-IDF Similarity ---
    if ICONS_DATA:
        # Build corpus (description + keywords for each icon)
        corpus = [
            f"{icon.get('description', '')} {' '.join(icon.get('keywords', []))}"
            for icon in ICONS_DATA
        ]
        similarities = calculate_similarity_batch(combined_text, corpus)

        results = []
        for icon, score in zip(ICONS_DATA, similarities):
            results.append({
                "name": icon["name"],
                "display_name": icon.get("display_name", icon["name"]),
                "description": icon.get("description", ""),
                "category": icon.get("category", ""),
                "similarity_score": score
            })

        results.sort(key=lambda x: x["similarity_score"], reverse=True)

        return {
            "suggested_icon": results[0] if results else {
                "name": "trophy.png",
                "display_name": "Trophy",
                "description": "Default achievement icon",
                "similarity_score": 0.5
            },
            "alternatives": results[1:top_k],
            "matching_method": "tfidf_similarity",
            "total_icons_available": len(ICONS_DATA)
        }

    # --- Case 2: Keyword Matching Fallback ---
    combined_text_lower = combined_text.lower()
    scores = {
        icon: sum(1 for kw in keywords if kw in combined_text_lower)
        for icon, keywords in ICON_KEYWORDS.items()
    }
    scores = {k: v for k, v in scores.items() if v > 0}

    if scores:
        sorted_icons = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        suggested, top_score = sorted_icons[0]
        alternatives = [
            {"name": icon, "similarity_score": score / 10}
            for icon, score in sorted_icons[1:top_k]
        ]
    else:
        suggested, top_score = "trophy.png", 7
        alternatives = [{"name": "goal.png", "similarity_score": 0.5}]

    return {
        "suggested_icon": {
            "name": suggested,
            "display_name": suggested.replace(".png", "").title(),
            "description": f"Contextually selected icon for {badge_name}",
            "similarity_score": top_score / 10
        },
        "alternatives": alternatives,
        "matching_method": "keyword_fallback",
        "total_icons_available": len(ICON_KEYWORDS)
    }
