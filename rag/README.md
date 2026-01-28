# RAG Vector Database System

This directory contains the RAG (Retrieval-Augmented Generation) system for badge generation with automatic vector database updates.

## Overview

The system uses FAISS vector search to retrieve similar badges as few-shot examples, improving consistency and quality of badge generation. New badges are automatically added to the vector database for continuous learning.

## Files

- **`build_vector_db.py`** - Initial build of FAISS index from training data
- **`retrieve_ob3.py`** - Retrieve similar badges from the vector database
- **`update_vector_db.py`** - Incrementally add new badges to the database

## How It Works

### 1. Initial Setup (One-time)

Build the vector database from your training dataset:

```bash
cd /home/prashanth/Documents/GitHub/slm
python rag/build_vector_db.py
```

This creates:
- `ob3_index.faiss` - FAISS vector index
- `ob3_metadata.json` - Badge metadata

### 2. Badge Generation with RAG

When a badge is generated:

1. **Retrieval**: Course input is embedded and top-2 similar badges are retrieved
2. **Few-Shot Prompting**: Retrieved badges are formatted as examples in the prompt
3. **Generation**: LLM generates new badge following the example format
4. **Auto-Update** (optional): New badge is added to vector database

```python
from app.services.badge_generator import generate_badge_metadata_async

# Automatically uses RAG and updates vector DB
result = await generate_badge_metadata_async(request)

# Check if vector DB was updated
if result["vector_db_updated"]:
    print("Badge added to vector DB!")
```

### 3. Manual Vector Database Updates

Add a single badge manually:

```python
from rag.update_vector_db import add_badge_to_vector_db

badge_data = {
    "badge_name": "Python Expert",
    "badge_description": "...",
    "criteria": {"narrative": "..."}
}

success = add_badge_to_vector_db(badge_data)
```

Batch add multiple badges:

```python
from rag.update_vector_db import batch_add_badges

badges = [badge1, badge2, badge3, ...]
count = batch_add_badges(badges)
print(f"Added {count} badges")
```

## Configuration

### Enable/Disable Auto-Update

Set in `.env` or environment:

```bash
# Enable auto-update (default)
AUTO_UPDATE_VECTOR_DB=true

# Disable auto-update
AUTO_UPDATE_VECTOR_DB=false
```

Or modify `app/core/config.py`:

```python
AUTO_UPDATE_VECTOR_DB: bool = True  # or False
```

## Benefits

### Consistency
- Similar course content → similar badge structure
- Reduces variance in output format

### Quality
- Model learns from validated, high-quality examples
- Follows proven badge patterns

### Determinism
- Same/similar inputs retrieve same examples
- More predictable outputs

### Continuous Learning
- Vector DB grows with each new badge
- System improves over time

## Vector Database Details

### Embedding Model
- **Model**: `sentence-transformers/all-mpnet-base-v2`
- **Dimension**: 768
- **Similarity**: Cosine (via normalized inner product)

### Index Type
- **FAISS**: IndexFlatIP (Inner Product)
- **Normalization**: L2 normalized vectors
- **Search**: Exact nearest neighbor

### Metadata Format

Each badge is stored with:

```json
{
  "name": "Badge Name",
  "description": "Badge description...",
  "criteria": {
    "narrative": "Criteria narrative..."
  },
  "courses": [...],
  "alignment": [...],
  "source": {...}
}
```

## Monitoring

### Check Vector DB Size

```python
import faiss
index = faiss.read_index("ob3_index.faiss")
print(f"Total badges in DB: {index.ntotal}")
```

### View Retrieved Examples

The badge generation result includes:

```json
{
  "badge_name": "...",
  "retrieved_examples": [
    {
      "badge_name": "Similar Badge 1",
      "similarity_score": 0.87
    },
    {
      "badge_name": "Similar Badge 2",
      "similarity_score": 0.82
    }
  ],
  "vector_db_updated": true
}
```

## Troubleshooting

### Vector DB Not Updating

1. Check setting: `settings.AUTO_UPDATE_VECTOR_DB` should be `True`
2. Check logs for errors
3. Verify index files exist and are writable
4. Check disk space

### Poor Retrieval Quality

- **Low similarity scores** (<0.5): Dataset may not contain similar badges
- **Irrelevant examples**: Course input may need more detail
- **Always same examples**: Vector DB may be too small, add more badges

### Rebuilding Index

If metadata gets corrupted or you need a fresh start:

```bash
# Backup current index
cp ob3_index.faiss ob3_index.faiss.backup
cp ob3_metadata.json ob3_metadata.json.backup

# Rebuild from training data
python rag/build_vector_db.py
```

## Performance

### Memory Usage
- **Index**: ~5.4 MB (for ~7000 badges)
- **Metadata**: ~7.0 MB
- **Embedding Model**: ~420 MB (loaded once, cached)

### Speed
- **Retrieval**: ~10-50ms for k=2
- **Adding single badge**: ~100-200ms
- **Batch add (100 badges)**: ~2-5 seconds

## Best Practices

1. **Keep vector DB synchronized** - Enable auto-update in production
2. **Monitor similarity scores** - Low scores (<0.6) indicate poor matches
3. **Periodic backups** - Backup index files regularly
4. **Quality control** - Review auto-added badges periodically
5. **Batch operations** - Use `batch_add_badges()` for bulk imports

## Badge Retrieval API

Retrieve similar badges from the vector database using course content:

### Using the API Endpoint

```bash
curl -X POST http://localhost:8000/badges/get-previous-badges \
  -H "Content-Type: application/json" \
  -d '{
    "course_input": "Introduction to Python programming...",
    "count": 4
  }'
```

### Using Python

```python
from rag.retrieve_ob3 import get_previous_badges

# Retrieve 4 similar badges
similar_badges = get_previous_badges(
    course_input="Introduction to Python programming...",
    k=4
)

for badge in similar_badges:
    print(f"Score: {badge['similarity_score']:.4f}")
    print(f"Name: {badge['name']}")
    print(f"Description: {badge['description']}")
```

### Response Format

```json
{
  "previous_badges": [
    {
      "similarity_score": 0.89,
      "badge_name": "Python Fundamentals",
      "badge_description": "...",
      "criteria": {"narrative": "..."},
      "image_base64": "data:image/png;base64,...",
      "skills": [...]
    }
  ],
  "total_count": 4
}
```

## Example Workflow

```python
# 1. Generate badge with RAG
result = await generate_badge_metadata_async(request)

# 2. Check which examples were used
print("Retrieved examples:")
for ex in result["retrieved_examples"]:
    print(f"  {ex['badge_name']} ({ex['similarity_score']:.2f})")

# 3. Verify auto-update
if result["vector_db_updated"]:
    print("✅ Badge added to vector DB")
else:
    print("❌ Vector DB not updated")

# 4. Use the badge
badge_name = result["badge_name"]
badge_desc = result["badge_description"]
```
