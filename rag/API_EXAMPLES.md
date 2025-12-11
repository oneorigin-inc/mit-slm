# API Examples for RAG Badge Generation

## Endpoints Overview

### 1. Non-Streaming with RAG
**Endpoint:** `POST /generate-badge-suggestions`
**Features:**
- RAG retrieval
- Auto vector DB update
- Complete response

### 2. Streaming with RAG
**Endpoint:** `POST /generate-badge-suggestions/stream-rag`
**Features:**
- RAG retrieval
- Real-time streaming
- Auto vector DB update

### 3. Original Streaming (No RAG)
**Endpoint:** `POST /generate-badge-suggestions/stream`
**Features:**
- No RAG
- Real-time streaming
- Backward compatible

## Postman Examples

### Example 1: Basic RAG Request (Non-Streaming)

**URL:** `http://localhost:8000/generate-badge-suggestions`

**Method:** POST

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "course_input": "This course covers Python programming fundamentals including variables, functions, loops, and object-oriented programming. Students will learn to build practical applications.",
  "badge_style": "",
  "badge_tone": "",
  "criterion_style": "",
  "badge_level": "",
  "institution": "",
  "custom_instructions": "",
  "enable_skill_extraction": false
}
```

**Response:**
```json
{
  "credentialSubject": {
    "achievement": {
      "criteria": {
        "narrative": "Recipients have demonstrated..."
      },
      "description": "Badge description...",
      "image": {
        "id": "https://example.com/achievements/badge_xyz/image",
        "image_base64": "data:image/png;base64,..."
      },
      "name": "Python Programming Fundamentals"
    }
  },
  "imageConfig": {...},
  "badge_id": "abc-123-def-456",
  "metrics": {
    "total_duration": 1234567,
    "eval_count": 150
  }
}
```

**What Happens:**
1. System retrieves 2 similar badges from vector DB
2. Formats them as few-shot examples
3. Generates new badge using examples
4. Auto-adds new badge to vector DB (if AUTO_UPDATE_VECTOR_DB=true)

### Example 2: RAG Streaming Request

**URL:** `http://localhost:8000/generate-badge-suggestions/stream-rag`

**Method:** POST

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "course_input": "Advanced machine learning course covering neural networks, deep learning, CNNs, RNNs, and transformers. Hands-on implementation using PyTorch.",
  "badge_style": "Technical",
  "badge_tone": "Authoritative",
  "criterion_style": "Task-Oriented",
  "badge_level": "Advanced",
  "institution": "Tech University",
  "custom_instructions": "Emphasize practical ML experience",
  "enable_skill_extraction": true
}
```

**Response (Streaming):**

Chunk 1 (token):
```
data: {"type":"token","content":"{","accumulated":"{","badge_id":"xyz-789"}

```

Chunk 2 (token):
```
data: {"type":"token","content":"\"badge_name\"","accumulated":"{\"badge_name\"","badge_id":"xyz-789"}

```

Final Chunk:
```
data: {"type":"final","content":{...full badge...,"retrieved_examples":[{"badge_name":"Deep Learning Specialist","similarity_score":0.89},{"badge_name":"Neural Networks Expert","similarity_score":0.85}],"vector_db_updated":true},"badge_id":"xyz-789","generation_time":3.45,"metrics":{...}}

```

**What Happens:**
1. RAG retrieval finds similar badges
2. Tokens stream in real-time
3. Final response includes:
   - Complete badge data
   - Retrieved examples used
   - Vector DB update status
4. New badge added to vector DB

### Example 3: With Custom Parameters

**URL:** `http://localhost:8000/generate-badge-suggestions`

**Body:**
```json
{
  "course_input": "Healthcare compliance training covering HIPAA regulations, patient privacy, data security, and legal requirements for medical professionals.",
  "badge_style": "Professional",
  "badge_tone": "Authoritative",
  "criterion_style": "Evidence-Based",
  "badge_level": "Intermediate",
  "institution": "Healthcare Institute",
  "custom_instructions": "Focus on regulatory compliance and legal aspects",
  "enable_skill_extraction": false
}
```

### Example 4: Minimal Request

**URL:** `http://localhost:8000/generate-badge-suggestions`

**Body:**
```json
{
  "course_input": "Introduction to Web Development: HTML, CSS, JavaScript basics",
  "badge_style": "",
  "badge_tone": "",
  "criterion_style": "",
  "badge_level": "",
  "institution": "",
  "custom_instructions": "",
  "enable_skill_extraction": false
}
```

Note: Empty parameters will be randomly selected by the system.

## Checking Vector DB Update

### Method 1: Check Response
Look for `vector_db_updated` field in response:

```json
{
  "credentialSubject": {...},
  "vector_db_updated": true
}
```

### Method 2: Check Database Stats
Run the stats script:

```bash
cd /home/prashanth/Documents/GitHub/slm
python rag/db_stats.py
```

Output:
```
VECTOR DATABASE STATISTICS
======================================================================

FILE INFORMATION:
   Index File:     ob3_index.faiss
   Size:           5.42 MB
   Last Modified:  2025-12-11 16:45:23

   Metadata File:  ob3_metadata.json
   Size:           7.05 MB
   Last Modified:  2025-12-11 16:45:23

INDEX STATISTICS:
   Total Badges:   7,001
   Vector Dim:     768
   Index Type:     IndexFlatIP

METADATA STATISTICS:
   Total Entries:  7,001

   Index and metadata are synchronized

RECENTLY ADDED (last 5):
   1. Python Programming Fundamentals
   2. Advanced Machine Learning Specialist
   3. Healthcare Compliance Certificate
   4. Web Development Basics
   5. Data Science Professional
```

## Testing RAG Quality

### Check Retrieved Examples

In the response, look at `retrieved_examples`:

```json
{
  "retrieved_examples": [
    {
      "badge_name": "Python Expert Certification",
      "similarity_score": 0.87
    },
    {
      "badge_name": "Advanced Python Developer",
      "similarity_score": 0.82
    }
  ]
}
```

**Quality Indicators:**
- Similarity scores > 0.7: Good match
- Similarity scores 0.5-0.7: Moderate match
- Similarity scores < 0.5: Weak match (may need more training data)

## Common Use Cases

### 1. Generate Badge with RAG
Use: `/generate-badge-suggestions` or `/generate-badge-suggestions/stream-rag`
Result: New badge + auto-added to vector DB

### 2. Test Without DB Update
Set `AUTO_UPDATE_VECTOR_DB=false` in `.env`
Use: Any RAG endpoint
Result: New badge generated but NOT added to DB

### 3. View RAG Examples Used
Use: `/generate-badge-suggestions/stream-rag`
Check: `retrieved_examples` in final response

### 4. Monitor DB Growth
Before: Run `python rag/db_stats.py`
Generate: Create badge via API
After: Run `python rag/db_stats.py` again
Compare: Total badge count should increase by 1

## Troubleshooting

### Issue: vector_db_updated is false

**Possible causes:**
1. `AUTO_UPDATE_VECTOR_DB=false` in settings
2. Vector DB files missing
3. Permissions issue on index files
4. Invalid badge data

**Solution:** Check logs for error messages

### Issue: Low similarity scores

**Possible causes:**
1. Small training dataset
2. Course content very different from existing badges
3. Need more diverse examples

**Solution:** Add more training data and rebuild index

### Issue: Same examples always retrieved

**Possible causes:**
1. Very small dataset
2. Course inputs too similar

**Solution:** Expand training dataset with diverse badges
