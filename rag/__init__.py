"""RAG (Retrieval-Augmented Generation) module for badge generation."""

from rag.retrieve_ob3 import (
    retrieve_badge,
    get_previous_badges,
    is_rag_available,
    reload_metadata,
    get_metadata_count,
)

from rag.update_vector_db import (
    add_badge_to_vector_db,
    batch_add_badges,
    format_badge_for_embedding,
)

__all__ = [
    # Retrieval functions
    "retrieve_badge",
    "get_previous_badges",
    "is_rag_available",
    "reload_metadata",
    "get_metadata_count",
    # Update functions
    "add_badge_to_vector_db",
    "batch_add_badges",
    "format_badge_for_embedding",
]
