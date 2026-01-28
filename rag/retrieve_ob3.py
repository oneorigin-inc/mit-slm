import json
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Get the directory where this script is located
RAG_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(RAG_DIR, "ob3_index.faiss")
META_FILE = os.path.join(RAG_DIR, "ob3_metadata.json")

# Global variables for lazy loading
_model: Optional[SentenceTransformer] = None
_index: Optional[faiss.Index] = None
_metadata: Optional[List[Dict[str, Any]]] = None


def _load_resources() -> bool:
    """Lazy load the embedding model, FAISS index, and metadata."""
    global _model, _index, _metadata

    if _model is None:
        logger.info("Loading sentence transformer model...")
        _model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

    if _index is None:
        if not os.path.exists(INDEX_FILE):
            logger.warning(f"FAISS index not found at {INDEX_FILE}. Run build_vector_db.py first.")
            return False
        logger.info(f"Loading FAISS index from {INDEX_FILE}")
        _index = faiss.read_index(INDEX_FILE)

    if _metadata is None:
        if not os.path.exists(META_FILE):
            logger.warning(f"Metadata file not found at {META_FILE}. Run build_vector_db.py first.")
            return False
        logger.info(f"Loading metadata from {META_FILE}")
        with open(META_FILE, "r", encoding="utf-8") as f:
            _metadata = json.load(f)

    return True


def is_rag_available() -> bool:
    """Check if RAG resources are available."""
    return os.path.exists(INDEX_FILE) and os.path.exists(META_FILE)


def get_metadata_count() -> int:
    """Get the count of badges in the metadata."""
    global _metadata
    if not _load_resources() or _metadata is None:
        return 0
    return len(_metadata)

def retrieve_badge(query: str, k: int = 3) -> List[Dict[str, Any]]:
    """Retrieve top-k similar OB3 badges and return name, description, criterion."""
    global _model, _index, _metadata

    # Lazy load resources
    if not _load_resources():
        logger.error("RAG resources not available")
        return []

    # Safety check after loading
    if _model is None or _index is None or _metadata is None:
        logger.error("RAG resources failed to load properly")
        return []

    # Encode & normalize query
    q_emb = _model.encode([query], convert_to_numpy=True).astype("float32")
    q_emb = q_emb / np.linalg.norm(q_emb, axis=1, keepdims=True)

    # FAISS search
    D, I = _index.search(q_emb, k)

    results = []
    for score, idx in zip(D[0], I[0]):
        if idx < 0 or idx >= len(_metadata):
            continue
        ach = _metadata[idx]  # This is the stored achievement metadata

        results.append({
            "score": float(score),
            "badge_name": ach.get("name", ""),
            "badge_description": ach.get("description", ""),
            "criterion": ach.get("criteria", {}).get("narrative", ""),
        })

    return results


def get_previous_badges(course_input: str, k: int = 4) -> List[Dict[str, Any]]:
    """
    Retrieve k previous similar badges from the database.
    Returns COMPLETE badge data including image, skills, and all configuration.

    Args:
        course_input: The course content to search for similar badges
        k: Number of badges to retrieve (default: 4)

    Returns:
        List of similar badges with their COMPLETE details and similarity scores
    """
    global _model, _index, _metadata

    # Lazy load resources
    if not _load_resources():
        logger.warning("RAG resources not available - returning empty list")
        return []

    # Safety check after loading
    if _model is None or _index is None or _metadata is None:
        logger.warning("RAG resources failed to load properly")
        return []

    # Encode & normalize query
    q_emb = _model.encode([course_input], convert_to_numpy=True).astype("float32")
    q_emb = q_emb / np.linalg.norm(q_emb, axis=1, keepdims=True)

    # FAISS search
    D, I = _index.search(q_emb, k)

    results = []
    for score, idx in zip(D[0], I[0]):
        if idx < 0 or idx >= len(_metadata):
            continue

        badge_data = _metadata[idx]

        # Return the COMPLETE badge data with similarity score
        result = {
            "similarity_score": round(float(score), 4),
            **badge_data  # Include all stored badge data
        }
        results.append(result)

    return results


def reload_metadata() -> bool:
    """Force reload of metadata and FAISS index from disk. Call after adding new badges."""
    global _metadata, _index
    _metadata = None
    _index = None  # Also reload FAISS index to include new badge vectors
    return _load_resources()


# Example usage
if __name__ == "__main__":
    new_course_input = """
     "course_name": "The Affordable Care Act of 2010",
        "description": "Gain a clear understanding of one of the most transformative healthcare laws in U.S. history. This course unpacks the Affordable Care Act (ACA), exploring its goals, key provisions, and lasting impact on the healthcare system. You\u2019ll learn how the ACA expanded health insurance coverage, addressed rising healthcare costs, and introduced Essential Health Benefits and preventive care requirements. Ideal for healthcare professionals, policy enthusiasts, and anyone looking to understand ACA\u2019s role in shaping modern healthcare, this course provides the knowledge you need to grasp both the intent and the real-world effects of this landmark legislation.",
        "competencies": [
          "Understand the goals and key provisions of the Affordable Care Act (ACA)",
          "Analyze the impact of the ACA on the healthcare system"
    """
    
    matches = retrieve_badge(new_course_input, k=3)
    
    for m in matches:
        print("\nSimilarity Score:", m["score"])
        print("Badge Name:", m["badge_name"])
        print("Description:", m["badge_description"])
        print("Criterion:", m["criterion"])
