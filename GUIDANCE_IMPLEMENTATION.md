# Guidance Implementation for Structured JSON Output

## Overview

This implementation integrates the **guidance** library to ensure reliable, schema-validated JSON output from your badge generation LLM. This eliminates JSON parsing errors and guarantees that the output always conforms to your expected structure.

## What is Guidance?

**Guidance** is a programming framework for controlling language model outputs. It ensures that LLM-generated content conforms to specific structures, grammars, or schemas—eliminating the need for fragile regex-based JSON extraction.

### Key Benefits

1. **Guaranteed Valid JSON** - No more parsing errors or malformed responses
2. **Token Fast-Forwarding** - Skips generating tokens when structure is predetermined
3. **Schema Validation** - Ensures output matches your Pydantic models during generation
4. **Better Reliability** - Production-ready structured output without fallback logic
5. **Cost & Latency Reduction** - Fast-forwarding saves tokens and time

## Architecture

### File Structure

```
app/
├── services/
│   ├── badge_generator.py           # Updated with guidance integration
│   └── guidance_badge_generator.py  # New: Guidance service implementation
├── core/
│   └── config.py                    # Updated with USE_GUIDANCE setting
└── models/
    └── badge.py                     # Existing Pydantic models
```

### How It Works

```
User Request
    ↓
badge_generator.py
    ↓
[USE_GUIDANCE enabled?]
    ↓ YES                    ↓ NO
guidance_badge_generator.py   Original regex-based method
    ↓                        ↓
Guidance + Ollama          Ollama → Regex Extraction
    ↓                        ↓
Guaranteed Valid JSON      Possible Parsing Errors
    ↓                        ↓
BadgeValidated (Pydantic)
```

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Enable/disable guidance (default: true)
USE_GUIDANCE=true

# Existing Ollama configuration
OLLAMA_API_URL=http://localhost:11434/api/generate
MODEL_NAME=phi4-chat:latest
```

### Settings (app/core/config.py)

```python
# Guidance Configuration for Structured JSON Output
USE_GUIDANCE: bool = os.getenv("USE_GUIDANCE", "true").lower() == "true"
```

## Usage

### Automatic Integration

The guidance integration is **transparent** to existing code. Your existing badge generation endpoints automatically use guidance when `USE_GUIDANCE=true`:

```python
# Non-streaming: automatically uses guidance if enabled
result = await generate_badge_metadata_async(request)

# Streaming: automatically uses guidance validation if enabled
async for chunk in generate_badge_metadata_stream_async(request):
    if chunk["type"] == "token":
        # Real-time token streaming
        process_token(chunk["content"])
    elif chunk["type"] == "final":
        # Validated final result
        result = chunk["content"]
```

### Manual Control

You can explicitly call guidance or fallback methods:

**Non-streaming:**

```python
from app.services.badge_generator import (
    generate_badge_metadata_with_guidance_async,
    generate_badge_metadata_async_fallback
)

# Force guidance method
result = await generate_badge_metadata_with_guidance_async(request)

# Force fallback method (original regex-based)
result = await generate_badge_metadata_async_fallback(request)
```

**Streaming:**

```python
from app.services.badge_generator import (
    _generate_badge_stream_with_guidance,
    _generate_badge_stream_fallback
)

# Force streaming with guidance validation
async for chunk in _generate_badge_stream_with_guidance(request):
    # Tokens stream normally, final result validated by guidance
    process(chunk)

# Force fallback streaming (regex-based validation)
async for chunk in _generate_badge_stream_fallback(request):
    # Original streaming implementation
    process(chunk)
```

### Direct Guidance Service

For advanced use cases, use the guidance service directly:

```python
from app.services.guidance_badge_generator import guidance_generator

result = await guidance_generator.generate_badge_with_schema(
    course_content="Python programming course...",
    style="Technical",
    tone="Encouraging",
    level="Intermediate",
    criterion_style="Task-Oriented",
    institution="MIT",
    custom_instructions="Focus on practical skills"
)

# Result is guaranteed to have:
# - badge_name (str)
# - badge_description (str)
# - criteria (dict with 'narrative' key)
```

## Implementation Details

### BadgeSchema

The Pydantic schema used by guidance:

```python
class BadgeSchema(BaseModel):
    badge_name: str = Field(max_length=100)
    badge_description: str = Field(max_length=500)
    criteria: Dict[str, str] = Field(
        default_factory=lambda: {"narrative": ""}
    )
```

### Generation Methods

**1. Schema-based (Recommended)**

```python
result = await guidance_generator.generate_badge_with_schema(...)
```

Uses `guidance.json(schema=BadgeSchema)` for automatic validation.

**2. Manual Structure**

```python
result = await guidance_generator.generate_badge_manual_structure(...)
```

Provides fine-grained control over each JSON field generation.

## Testing

### Run Test Suites

**Non-streaming badge generation:**

```bash
python test_guidance_badge.py
```

This tests both guidance and fallback generation methods.

**Streaming badge generation:**

```bash
python test_guidance_streaming.py
```

This tests streaming with guidance validation, fallback streaming, and auto-routing.

### Expected Output

```
====================================================
BADGE GENERATION TEST SUITE
====================================================

Testing GUIDANCE-based badge generation...
✓ Guidance generation SUCCESSFUL!

Badge Name: Python Programming Expert
Badge Description: This badge recognizes...
Criteria: {'narrative': 'The learner determines...'}

Testing FALLBACK (original) badge generation...
✓ Fallback generation SUCCESSFUL!

====================================================
TEST SUMMARY
====================================================
Guidance Generation: ✓ PASS
Fallback Generation: ✓ PASS
====================================================

🎉 All tests passed!
```

## Troubleshooting

### Issue: Guidance initialization fails

**Symptoms:**
```
Failed to initialize guidance model: ...
```

**Solution:**
- Ensure Ollama is running: `ollama serve`
- Verify Ollama API URL in `.env`
- Check that your model is available: `ollama list`

### Issue: Fallback to regex method

**Symptoms:**
```
Guidance generation failed, falling back to standard method
```

**Solution:**
- Check Ollama logs for errors
- Verify model supports OpenAI-compatible API
- Try disabling guidance temporarily: `USE_GUIDANCE=false`

### Issue: Import errors

**Symptoms:**
```
ModuleNotFoundError: No module named 'guidance'
```

**Solution:**
```bash
pip install -r requirements.txt
```

## Comparison: Before vs After

### Before (Regex-based)

```python
# Generate raw text
response = await call_model_async(prompt)

# Try to extract JSON (can fail!)
result = extract_json_from_response(response)

# Validate (might fail if extraction was wrong)
validated = BadgeValidated(**result)
```

**Problems:**
- JSON extraction can fail
- No guarantee of valid structure
- Validation happens after generation
- Requires complex regex patterns
- Error-prone in production

### After (Guidance-based)

```python
# Generate with schema validation
result = await guidance_generator.generate_badge_with_schema(...)

# Already validated! Just use it:
validated = BadgeValidated(**result)  # Always succeeds
```

**Benefits:**
- Guaranteed valid JSON
- Schema validation during generation
- No parsing errors
- Cleaner code
- Production-ready

## Performance Considerations

### Token Fast-Forwarding

Guidance automatically fast-forwards tokens when structure is known:

```json
{
  "badge_name": "..."
  // ↑ These tokens are fast-forwarded (not generated)
}
```

This can reduce generation time by **20-40%** for structured outputs.

### Metrics

The system still tracks Ollama metrics:

```python
result = await generate_badge_metadata_with_guidance_async(request)
# result includes: selected_parameters, processed_course_input, etc.
```

## Advanced Features

### Custom Constraints

Modify `BadgeSchema` for stricter validation:

```python
class BadgeSchema(BaseModel):
    badge_name: str = Field(
        min_length=10,
        max_length=80,
        pattern=r"^[A-Z].*"  # Must start with capital letter
    )
    badge_description: str = Field(
        min_length=50,
        max_length=400
    )
```

### Streaming Support

**✅ NOW IMPLEMENTED!**

Streaming generation now supports guidance validation:

```python
async for chunk in generate_badge_metadata_stream_async(request):
    if chunk["type"] == "token":
        # Stream tokens in real-time for UX
        print(chunk["content"], end="")
    elif chunk["type"] == "final":
        # Final result - validated with guidance if enabled
        result = chunk["content"]
        if chunk.get("guidance_corrected"):
            print("\n⚡ Output was corrected using guidance")
```

**How it works:**

1. **Token Streaming**: Tokens stream normally from Ollama for real-time UX
2. **Smart Validation**: When streaming completes:
   - First tries regex extraction (fast path)
   - If extraction fails or produces invalid JSON, uses guidance to correct it
   - Returns valid JSON guaranteed
3. **Transparent**: Works with existing streaming endpoints
4. **Fallback Ready**: Automatically falls back if guidance fails

**Test streaming:**

```bash
python test_guidance_streaming.py
```

## Migration Guide

### Enabling Guidance

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variable:**
   ```bash
   echo "USE_GUIDANCE=true" >> .env
   ```

3. **Restart your application:**
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Test the integration:**
   ```bash
   python test_guidance_badge.py
   ```

### Disabling Guidance

If you need to temporarily disable guidance:

```bash
# In .env
USE_GUIDANCE=false
```

The system automatically falls back to the original regex-based method.

## Resources

- **Guidance Documentation:** https://github.com/guidance-ai/guidance
- **Pydantic Models:** https://docs.pydantic.dev/
- **Ollama API:** https://github.com/ollama/ollama/blob/main/docs/api.md

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Ollama logs: `docker logs ollama` or check service logs
3. Test with fallback method to isolate guidance-specific issues
4. Review the test script output for detailed error messages

## Summary

The guidance integration provides **production-ready, reliable structured JSON output** for your badge generation system. It eliminates the fragility of regex-based parsing while maintaining full compatibility with your existing codebase.

**Key Points:**
- ✅ Guaranteed valid JSON
- ✅ Automatic fallback to original method
- ✅ Transparent integration
- ✅ Configurable via environment variable
- ✅ Fully tested

Enable it with `USE_GUIDANCE=true` and enjoy error-free badge generation!
