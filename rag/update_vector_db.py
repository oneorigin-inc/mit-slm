"""Incrementally update the vector database with new badge metadata"""
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import os
from typing import Dict, Any

# Get the directory where this script is located
RAG_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(RAG_DIR, "ob3_index.faiss")
META_FILE = os.path.join(RAG_DIR, "ob3_metadata.json")
EMBED_MODEL = "sentence-transformers/all-mpnet-base-v2"


def format_badge_for_embedding(badge_data: Dict[str, Any]) -> str:
    """
    Format badge data into text for embedding.
    Should match the format used in build_vector_db.py

    Handles both:
    - New format: complete BadgeResponse with credentialSubject
    - Legacy format: flat badge_name, badge_description, criteria
    """
    parts = []

    # Check if this is a complete BadgeResponse format
    if 'credentialSubject' in badge_data:
        achievement = badge_data.get('credentialSubject', {}).get('achievement', {})
        parts.append(f"Name: {achievement.get('name', '')}")
        parts.append(f"Description: {achievement.get('description', '')}")
        criteria = achievement.get('criteria', {})
        parts.append(f"Criteria: {criteria.get('narrative', '')}")

        # Add alignment/ESCO skills for better semantic matching
        alignment = achievement.get('alignment', [])
        if alignment:
            skill_names = [a.get('targetName', '') for a in alignment if a.get('targetName')]
            if skill_names:
                parts.append(f"Skills: {', '.join(skill_names)}")
    else:
        # Legacy format
        parts.append(f"Name: {badge_data.get('badge_name', badge_data.get('name', ''))}")
        parts.append(f"Description: {badge_data.get('badge_description', badge_data.get('description', ''))}")
        criteria = badge_data.get('criteria', {})
        parts.append(f"Criteria: {criteria.get('narrative', '')}")

        # # Add alignment if present in legacy format
        # alignment = badge_data.get('alignment', [])
        # if alignment:
        #     skill_names = [a.get('targetName', '') for a in alignment if a.get('targetName')]
        #     if skill_names:
        #         parts.append(f"Skills: {', '.join(skill_names)}")

    # Add course information - check both course_input and courses array
    if 'course_input' in badge_data and badge_data.get('course_input'):
        parts.append(f"Course: {badge_data.get('course_input', '')}")
    elif badge_data.get('courses') and len(badge_data['courses']) > 0:
        for course in badge_data['courses']:
            if course.get('description'):
                parts.append(f"Course: {course['description']}")

    # Add skills array for better semantic matching (LAiSER skills)
    skills = badge_data.get('skills', [])
    if skills:
        skill_names = [s.get('skill_name', s.get('name', '')) for s in skills if s]
        if skill_names:
            parts.append(f"LAiSER Skills: {', '.join(skill_names)}")

    return "\n".join(parts)


# Default similarity threshold - badges with similarity above this are considered duplicates
SIMILARITY_THRESHOLD = 0.95


def add_badge_to_vector_db(badge_data: Dict[str, Any], model=None, course_input: str = None, similarity_threshold: float = None):
    """
    Add a single new badge to the existing FAISS index and metadata.
    Stores the COMPLETE badge output including image, skills, and configuration.

    Checks for duplicate badges using similarity threshold before adding.

    Args:
        badge_data: Complete badge response dictionary (BadgeResponse format) or legacy format
        model: Optional pre-loaded SentenceTransformer model (for efficiency)
        course_input: Original course input text for better retrieval
        similarity_threshold: Threshold above which badges are considered duplicates (default: 0.95)

    Returns:
        dict: {"success": bool, "added": bool, "reason": str, "similar_badge": str|None}
    """
    threshold = similarity_threshold if similarity_threshold is not None else SIMILARITY_THRESHOLD

    try:
        # Check if index and metadata files exist
        if not os.path.exists(INDEX_FILE):
            print(f"ERROR: {INDEX_FILE} not found. Run build_vector_db.py first.")
            return {"success": False, "added": False, "reason": "Index file not found", "similar_badge": None}

        if not os.path.exists(META_FILE):
            print(f"ERROR: {META_FILE} not found. Run build_vector_db.py first.")
            return {"success": False, "added": False, "reason": "Metadata file not found", "similar_badge": None}

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

        # Add course_input to badge_data for embedding if provided
        embedding_data = badge_data.copy()
        if course_input:
            embedding_data['course_input'] = course_input

        # Format badge for embedding
        badge_text = format_badge_for_embedding(embedding_data)

        # Generate embedding
        print("Computing embedding for new badge...")
        embedding = model.encode([badge_text], convert_to_numpy=True)

        # Normalize embedding (same as build_vector_db.py)
        embedding = embedding.astype("float32")
        embedding = embedding / np.linalg.norm(embedding, axis=1, keepdims=True)

        # Check for duplicate badges using similarity threshold
        if initial_count > 0:
            D, I = index.search(embedding, 1)  # Find the most similar badge
            top_similarity = float(D[0][0])
            top_idx = int(I[0][0])

            if top_similarity >= threshold:
                similar_badge_name = metadata[top_idx].get("name", "Unknown") if top_idx < len(metadata) else "Unknown"
                print(f"SKIPPED: Badge too similar to existing badge '{similar_badge_name}' (similarity: {top_similarity:.4f} >= {threshold})")
                return {
                    "success": True,
                    "added": False,
                    "reason": f"Duplicate detected (similarity: {top_similarity:.4f})",
                    "similar_badge": similar_badge_name,
                    "similarity_score": top_similarity
                }

        # Add to FAISS index (no duplicate found)
        index.add(embedding)  # type: ignore[arg-type]

        # Prepare COMPLETE metadata entry - store everything
        if 'credentialSubject' in badge_data:
            # New BadgeResponse format - store COMPLETE data as-is
            achievement = badge_data.get('credentialSubject', {}).get('achievement', {})

            # Extract image data - handle both formats:
            # Format 1: {"id": "data:image/png;base64,...", "type": "Image"}
            # Format 2: {"id": "url", "image_base64": "..."}
            image_data = achievement.get("image", {})
            image_base64 = None
            if image_data:
                # Check if 'id' contains base64 data directly
                image_id = image_data.get("id", "")
                if image_id and image_id.startswith("data:image"):
                    image_base64 = image_id  # The id IS the base64 data
                else:
                    image_base64 = image_data.get("image_base64")

            from datetime import datetime
            new_metadata = {
                # Core badge info (for backward compatibility and quick access)
                "name": achievement.get("name", ""),
                "description": achievement.get("description", ""),
                "criteria": achievement.get("criteria", {}),
                # COMPLETE credentialSubject - stored exactly as provided
                "credentialSubject": badge_data.get("credentialSubject", {}),
                # Image data (extracted for quick access)
                "imageConfig": badge_data.get("imageConfig"),
                "image_base64": image_base64,
                # Alignment/ESCO skills (stored in achievement, also extracted for quick access)
                "alignment": achievement.get("alignment", []),
                # Skills/LAiSER data
                "skills": badge_data.get("skills", []),
                # Configuration
                "badge_configuration": badge_data.get("badge_configuration", {}),
                "badge_id": badge_data.get("badge_id", ""),
                # Metrics
                "metrics": badge_data.get("metrics", {}),
                # Flags
                "enable_image_generation": badge_data.get("enable_image_generation", False),
                "enable_skill_extraction": badge_data.get("enable_skill_extraction", False),
                # Original course input for reference
                "course_input": course_input or "",
                # Source info
                "source": {"type": "generated", "timestamp": datetime.now().isoformat()}
            }
        else:
            # Legacy format - convert to new structure
            courses = badge_data.get("courses", [])
            if not courses and course_input:
                courses = [{
                    "course_name": badge_data.get("badge_name", "Course"),
                    "description": course_input,
                    "competencies": []
                }]

            new_metadata = {
                "name": badge_data.get("badge_name", badge_data.get("name", "")),
                "description": badge_data.get("badge_description", badge_data.get("description", "")),
                "criteria": badge_data.get("criteria", {}),
                "courses": courses,
                "alignment": badge_data.get("alignment", []),
                "source": badge_data.get("source", {}),
                "course_input": course_input or "",
                # Include any extra fields
                "skills": badge_data.get("skills", []),
                "imageConfig": badge_data.get("imageConfig"),
                "badge_configuration": badge_data.get("badge_configuration", {}),
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

        badge_name = new_metadata.get("name", "Unknown")
        print(f"Successfully added badge to vector DB!")
        print(f"   Index size: {initial_count} -> {index.ntotal} (+1)")
        print(f"   Badge: {badge_name}")

        return {
            "success": True,
            "added": True,
            "reason": "Badge added successfully",
            "similar_badge": None,
            "badge_name": badge_name
        }

    except Exception as e:
        print(f"ERROR adding badge to vector DB: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "added": False,
            "reason": f"Error: {str(e)}",
            "similar_badge": None
        }


def batch_add_badges(badges: list, model=None):
    """
    Add multiple badges to the vector database efficiently.
    Stores COMPLETE badge data including image, skills, and configuration.

    Args:
        badges: List of badge dictionaries (can be BadgeResponse format or legacy)
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

        # Add all metadata with COMPLETE data
        from datetime import datetime
        timestamp = datetime.now().isoformat()

        for badge in badges:
            if 'credentialSubject' in badge:
                # New BadgeResponse format - store COMPLETE data as-is
                achievement = badge.get('credentialSubject', {}).get('achievement', {})

                # Extract image data - handle both formats
                image_data = achievement.get("image", {})
                image_base64 = None
                if image_data:
                    image_id = image_data.get("id", "")
                    if image_id and image_id.startswith("data:image"):
                        image_base64 = image_id
                    else:
                        image_base64 = image_data.get("image_base64")

                new_metadata = {
                    "name": achievement.get("name", ""),
                    "description": achievement.get("description", ""),
                    "criteria": achievement.get("criteria", {}),
                    "credentialSubject": badge.get("credentialSubject", {}),
                    "imageConfig": badge.get("imageConfig"),
                    "image_base64": image_base64,
                    "alignment": achievement.get("alignment", []),
                    "skills": badge.get("skills", []),
                    "badge_configuration": badge.get("badge_configuration", {}),
                    "badge_id": badge.get("badge_id", ""),
                    "metrics": badge.get("metrics", {}),
                    "enable_image_generation": badge.get("enable_image_generation", False),
                    "enable_skill_extraction": badge.get("enable_skill_extraction", False),
                    "course_input": badge.get("course_input", ""),
                    "source": {"type": "generated", "timestamp": timestamp}
                }
            else:
                # Legacy format
                courses = badge.get("courses", [])
                if not courses and badge.get("course_input"):
                    courses = [{
                        "course_name": badge.get("badge_name", "Course"),
                        "description": badge.get("course_input"),
                        "competencies": []
                    }]

                new_metadata = {
                    "name": badge.get("badge_name", badge.get("name", "")),
                    "description": badge.get("badge_description", badge.get("description", "")),
                    "criteria": badge.get("criteria", {}),
                    "courses": courses,
                    "alignment": badge.get("alignment", []),
                    "source": badge.get("source", {}),
                    "course_input": badge.get("course_input", ""),
                    "skills": badge.get("skills", []),
                    "imageConfig": badge.get("imageConfig"),
                    "badge_configuration": badge.get("badge_configuration", {}),
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
