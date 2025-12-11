import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

INDEX_FILE = "ob3_index.faiss"
META_FILE  = "ob3_metadata.json"

# Load embedding model
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

# Load index + metadata
index = faiss.read_index(INDEX_FILE)
with open(META_FILE, "r", encoding="utf-8") as f:
    metadata = json.load(f)

def retrieve_badge(query, k=3):
    """Retrieve top-k similar OB3 badges and return name, description, criterion."""
    
    # Encode & normalize query
    q_emb = model.encode([query], convert_to_numpy=True).astype("float32")
    q_emb = q_emb / np.linalg.norm(q_emb, axis=1, keepdims=True)

    # FAISS search
    D, I = index.search(q_emb, k)

    results = []
    for score, idx in zip(D[0], I[0]):
        ach = metadata[idx]  # This is the stored achievement metadata

        results.append({
            "score": float(score),
            "badge_name": ach.get("name", ""),
            "badge_description": ach.get("description", ""),
            "criterion": ach.get("criteria", {}).get("narrative", ""),
        })

    return results


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
