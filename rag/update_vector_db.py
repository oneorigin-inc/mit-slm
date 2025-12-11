"""Incrementally update the vector database with new badge metadata"""
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import os
from typing import Dict, Any

INDEX_FILE = "ob3_index.faiss"
META_FILE = "ob3_metadata.json"
EMBED_MODEL = "sentence-transformers/all-mpnet-base-v2"


def format_badge_for_embedding(badge_data: Dict[str, Any]) -> str:
    """
    Format badge data into text for embedding.
    Should match the format used in build_vector_db.py
    """
    parts = []

    # Core fields
    parts.append(f"Name: {badge_data.get('badge_name', '')}")
    parts.append(f"Description: {badge_data.get('badge_description', '')}")

    # Criteria
    criteria = badge_data.get('criteria', {})
    parts.append(f"Criteria: {criteria.get('narrative', '')}")

    # Add course information - check both course_input and courses array
    if 'course_input' in badge_data and badge_data.get('course_input'):
        parts.append(f"Course: {badge_data.get('course_input', '')}")
    elif badge_data.get('courses') and len(badge_data['courses']) > 0:
        for course in badge_data['courses']:
            if course.get('description'):
                parts.append(f"Course: {course['description']}")

    return "\n".join(parts)


def add_badge_to_vector_db(badge_data: Dict[str, Any], model=None):
    """
    Add a single new badge to the existing FAISS index and metadata.

    Args:
        badge_data: Dictionary containing badge_name, badge_description, criteria
        model: Optional pre-loaded SentenceTransformer model (for efficiency)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if index and metadata files exist
        if not os.path.exists(INDEX_FILE):
            print(f"ERROR: {INDEX_FILE} not found. Run build_vector_db.py first.")
            return False

        if not os.path.exists(META_FILE):
            print(f"ERROR: {META_FILE} not found. Run build_vector_db.py first.")
            return False

        # Load existing index
        print(f"Loading existing FAISS index ({INDEX_FILE})...")
        index = faiss.read_index(INDEX_FILE)
        initial_count = index.ntotal

        # Load existing metadata
        print(f"Loading existing metadata ({META_FILE})...")
        with open(META_FILE, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Load embedding model if not provided
        if model is None:
            print(f"Loading embedding model: {EMBED_MODEL}")
            model = SentenceTransformer(EMBED_MODEL)

        # Format badge for embedding
        badge_text = format_badge_for_embedding(badge_data)

        # Generate embedding
        print("Computing embedding for new badge...")
        embedding = model.encode([badge_text], convert_to_numpy=True)

        # Normalize embedding (same as build_vector_db.py)
        embedding = embedding.astype("float32")
        embedding = embedding / np.linalg.norm(embedding, axis=1, keepdims=True)

        # Add to FAISS index
        index.add(embedding)  # type: ignore[arg-type]

        # Prepare metadata entry (matching the format from build_vector_db.py)
        # Handle course_input - convert to OB3 course structure if provided
        courses = badge_data.get("courses", [])
        if not courses and badge_data.get("course_input"):
            # Create OB3-compliant course object from course_input
            courses = [{
                "course_name": badge_data.get("badge_name", "Course"),
                "description": badge_data.get("course_input"),
                "competencies": []
            }]

        new_metadata = {
            "name": badge_data.get("badge_name"),
            "description": badge_data.get("badge_description"),
            "criteria": badge_data.get("criteria", {}),
            "courses": courses,
            "alignment": badge_data.get("alignment", []),
            "source": badge_data.get("source", {})
        }

        # Append to metadata
        metadata.append(new_metadata)

        # Save updated index
        print(f"Saving updated FAISS index...")
        faiss.write_index(index, INDEX_FILE)

        # Save updated metadata
        print(f"Saving updated metadata...")
        with open(META_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        print(f"Successfully added badge to vector DB!")
        print(f"   Index size: {initial_count} -> {index.ntotal} (+1)")
        print(f"   Badge: {badge_data.get('badge_name')}")

        return True

    except Exception as e:
        print(f"ERROR adding badge to vector DB: {e}")
        import traceback
        traceback.print_exc()
        return False


def batch_add_badges(badges: list, model=None):
    """
    Add multiple badges to the vector database efficiently.

    Args:
        badges: List of badge dictionaries
        model: Optional pre-loaded SentenceTransformer model

    Returns:
        int: Number of badges successfully added
    """
    if not badges:
        print("No badges to add.")
        return 0

    try:
        # Load existing index and metadata
        index = faiss.read_index(INDEX_FILE)
        with open(META_FILE, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        initial_count = index.ntotal

        # Load model once
        if model is None:
            print(f"Loading embedding model: {EMBED_MODEL}")
            model = SentenceTransformer(EMBED_MODEL)

        # Format all badges for embedding
        texts = [format_badge_for_embedding(badge) for badge in badges]

        # Generate embeddings in batch
        print(f"Computing embeddings for {len(badges)} badges...")
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)

        # Normalize embeddings
        embeddings = embeddings.astype("float32")
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms

        # Add to FAISS index
        index.add(embeddings)  # type: ignore[arg-type]

        # Add all metadata
        for badge in badges:
            # Handle course_input - convert to OB3 course structure if provided
            courses = badge.get("courses", [])
            if not courses and badge.get("course_input"):
                # Create OB3-compliant course object from course_input
                courses = [{
                    "course_name": badge.get("badge_name", "Course"),
                    "description": badge.get("course_input"),
                    "competencies": []
                }]

            new_metadata = {
                "name": badge.get("badge_name"),
                "description": badge.get("badge_description"),
                "criteria": badge.get("criteria", {}),
                "courses": courses,
                "alignment": badge.get("alignment", []),
                "source": badge.get("source", {})
            }
            metadata.append(new_metadata)

        # Save updated index and metadata
        faiss.write_index(index, INDEX_FILE)
        with open(META_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        print(f"Successfully added {len(badges)} badges!")
        print(f"   Index size: {initial_count} -> {index.ntotal} (+{len(badges)})")

        return len(badges)

    except Exception as e:
        print(f"ERROR in batch add: {e}")
        import traceback
        traceback.print_exc()
        return 0


# Example usage
if __name__ == "__main__":
    # Example: Add a single badge
    sample_badge = {
        "badge_name": "Python Expert",
        "badge_description": "Demonstrates advanced Python programming skills",
        "criteria": {
            "narrative": "The learner has completed advanced Python coursework including object-oriented programming, decorators, and async programming."
        }
    }

    add_badge_to_vector_db(sample_badge)
