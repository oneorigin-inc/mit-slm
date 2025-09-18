# main.py -
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import json
import logging

app = FastAPI()
logger = logging.getLogger("uvicorn.error")

# -------------------------
# CONFIGURATION
# -------------------------
MODEL_CONFIG = {
    "model_name": "phi-4-ob-badge-generator:latest",
    "temperature": 0.2,
    "top_p": 0.8,
    "top_k": 30,
    "num_predict": 600,
    "repeat_penalty": 1.05,
    "num_ctx": 4096,
    "stop": ["<|end|>", "}\n\n"]
}

OLLAMA_API = "http://localhost:11434/api/generate"

# -------------------------
# HELPER FUNCTIONS
# -------------------------
def build_prompt(course_input: str) -> str:
    """Build simple prompt for badge generation."""
    prompt = f"""COURSE CONTENT:
{course_input}

Generate Open Badges 3.0 compliant JSON metadata. Return a valid JSON object with exact schema:
{{
    "name": "string",
    "description": "string", 
    "criteria": {{
        "narrative": "string"
    }}
}}"""
    return prompt

def find_balanced_json(text: str) -> str | None:
    """Find balanced JSON object in text."""
    start = text.find('{')
    if start == -1:
        return None
    
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return None

def extract_json_from_text(text: str) -> dict:
    """Extract JSON object from model response text."""
    if not text:
        raise ValueError("Empty model response")
    
    s = text.strip()
    
    # Try direct JSON parsing first
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    
    # Try to find balanced JSON
    candidate = find_balanced_json(s)
    if candidate:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    
    # Try extracting between first { and last }
    first = s.find('{')
    last = s.rfind('}')
    if first != -1 and last != -1 and last > first:
        sub = s[first:last+1]
        try:
            return json.loads(sub)
        except json.JSONDecodeError:
            pass
    
    raise ValueError("No valid JSON found in model response")

async def call_model_async(prompt: str) -> str:
    """Call the badge generation model."""
    payload = {
        "model": MODEL_CONFIG["model_name"],
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": MODEL_CONFIG["temperature"],
            "top_p": MODEL_CONFIG["top_p"],
            "top_k": MODEL_CONFIG["top_k"],
            "num_predict": MODEL_CONFIG["num_predict"],
            "repeat_penalty": MODEL_CONFIG["repeat_penalty"],
            "num_ctx": MODEL_CONFIG["num_ctx"],
            "stop": MODEL_CONFIG["stop"]
        }
    }
    
    timeout = httpx.Timeout(300.0, read=330.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(OLLAMA_API, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Model server error {resp.status_code}: {resp.text[:200]}")
        
        try:
            response_json = resp.json()
            return response_json.get("response", "") or response_json.get("output", "") or json.dumps(response_json)
        except Exception:
            return resp.text

# -------------------------
# PYDANTIC MODELS
# -------------------------
class CourseInput(BaseModel):
    course_input: str

class BadgeResponse(BaseModel):
    name: str
    description: str
    criteria: dict

# -------------------------
# API ENDPOINT
# -------------------------
@app.post("/generate_badge", response_model=BadgeResponse)
async def generate_badge(request: CourseInput):
    """
    Generate badge metadata from course input.
    Returns badge JSON with name, description, and criteria narrative.
    """
    try:
        # Build prompt and call model
        prompt = build_prompt(request.course_input)
        response_text = await call_model_async(prompt)
        
        # Extract and validate JSON
        badge_json = extract_json_from_text(response_text)
        
        # Ensure required fields exist
        if not all(key in badge_json for key in ["name", "description", "criteria"]):
            raise ValueError("Missing required fields in model response")
        
        if not isinstance(badge_json.get("criteria"), dict) or "narrative" not in badge_json["criteria"]:
            raise ValueError("Invalid criteria structure in model response")
        
        return BadgeResponse(
            name=badge_json["name"],
            description=badge_json["description"],
            criteria=badge_json["criteria"]
        )
        
    except Exception as e:
        logger.exception("Error generating badge: %s", e)
        raise HTTPException(status_code=500, detail=f"Badge generation failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
