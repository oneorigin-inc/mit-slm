import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# Get the directory where this script is located
RAG_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_JSON = os.path.join(RAG_DIR, "training_data_set_20250923_ob3.json")
OUTPUT_INDEX = os.path.join(RAG_DIR, "ob3_index.faiss")
OUTPUT_META = os.path.join(RAG_DIR, "ob3_metadata.json")

EMBED_MODEL = "sentence-transformers/all-mpnet-base-v2"   # embedding model
EMBED_DIM = 768                                            # mpnet dimension


def extract_text_from_ob3(obj):
    """Extracts text to embed from one OB3 item."""

    ach = obj["credentialSubject"]["achievement"]

    parts = []

    # core fields
    parts.append(f"Name: {ach.get('name','')}")
    parts.append(f"Description: {ach.get('description','')}")
    
    criteria = ach.get("criteria", {})
    parts.append(f"Criteria: {criteria.get('narrative','')}")

    # courses
    if "courses" in ach:
        course_texts = []
        for c in ach["courses"]:
            course_texts.append(
                f"{c.get('course_name','')}: {c.get('description','')}"
            )
        if course_texts:
            parts.append("Courses: " + " || ".join(course_texts))

    return "\n".join(parts)


def build_vector_db():
    print("Loading OB3 dataset...")
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loaded {len(data)} OB3 items.")

    # Prepare embeddings text + metadata
    texts = []
    metadata = []

    for item in data:
        text = extract_text_from_ob3(item)
        texts.append(text)

        # minimal metadata for retrieval
        ach = item["credentialSubject"]["achievement"]
        metadata.append({
            "name": ach.get("name"),
            "description": ach.get("description"),
            "criteria": ach.get("criteria", {}),
            "courses": ach.get("courses", []),
            "alignment": ach.get("alignment", []),
            "source": ach.get("source", {})
        })

    # Load embedding model
    print("Loading embedding model:", EMBED_MODEL)
    model = SentenceTransformer(EMBED_MODEL)

    print("Computing embeddings...")
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)

    # convert to float32 + normalize for cosine similarity
    embeddings = embeddings.astype("float32")
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms

    dim = embeddings.shape[1]
    print("Embedding matrix:", embeddings.shape)

    # Build FAISS index (inner product = cosine on normalized vectors)
    index = faiss.IndexFlatIP(dim)
    # Add embeddings to index (embeddings must be float32 numpy array)
    index.add(embeddings)  # type: ignore[arg-type]

    print(f"FAISS index built: {index.ntotal} vectors")

    # Save files
    faiss.write_index(index, OUTPUT_INDEX)
    print("Saved FAISS index →", OUTPUT_INDEX)

    with open(OUTPUT_META, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("Saved metadata →", OUTPUT_META)


if __name__ == "__main__":
    build_vector_db()
