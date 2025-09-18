# main.py - Badge Generation Only (Version 1)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List, Dict, Any
import httpx
import json
import time
from datetime import datetime
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

STYLE_DESCRIPTIONS = {
    "Professional": "Use formal, business-oriented language emphasizing industry standards and career advancement.",
    "Academic": "Use scholarly language emphasizing learning outcomes and academic rigor.",
    "Industry": "Use sector-specific terminology focusing on job-readiness and practical applications.",
    "Technical": "Use precise technical language with emphasis on tools and measurable outcomes.",
    "Creative": "Use engaging language highlighting innovation and problem-solving."
}

TONE_DESCRIPTIONS = {
    "Authoritative": "Confident, definitive tone with institutional credibility.",
    "Encouraging": "Motivating, supportive tone inspiring continued learning.",
    "Detailed": "Comprehensive detail with examples and specific metrics.",
    "Concise": "Short, direct guidance focusing on essential information.",
    "Engaging": "Dynamic, compelling language to capture attention."
}

LEVEL_DESCRIPTIONS = {
    "Beginner": "Target learners with minimal prior knowledge; focus on foundations.",
    "Intermediate": "Target learners with basic familiarity; emphasize applied tasks.",
    "Advanced": "Target learners with solid foundations; emphasize complex problem solving."
}

CRITERION_TEMPLATES = {
    "Task-Oriented": "[Action verb], [action verb], [action verb]... (imperative commands directing learners to perform tasks)",
    "Evidence-Based": "Learner has/can/successfully [action verb], has/can/effectively [action verb], has/can/accurately [action verb]... (focusing on demonstrated abilities and accomplishments)",
    "Outcome-Focused": "Students will be able to [action verb], will be prepared to [action verb], will [action verb]... (future tense emphasizing expected outcomes and capabilities)"
}

# In-memory history
badge_history: List[Dict[str, Any]] = []

# -------------------------
# HELPER FUNCTIONS
# -------------------------
def build_prompt(request) -> str:
    """Build prompt for badge generation model."""
    style_instruction = STYLE_DESCRIPTIONS.get(request.badge_style, STYLE_DESCRIPTIONS["Professional"])
    tone_instruction = TONE_DESCRIPTIONS.get(request.badge_tone, TONE_DESCRIPTIONS["Authoritative"])
    level_instruction = LEVEL_DESCRIPTIONS.get(request.badge_level, LEVEL_DESCRIPTIONS["Intermediate"]) if request.badge_level else ""
    criterion_instruction = CRITERION_TEMPLATES.get(request.criteria_template, CRITERION_TEMPLATES["Task-Oriented"])

    prompt = f"""STYLE: {style_instruction}
TONE: {tone_instruction}"""

    if level_instruction:
        prompt += f"\nLEVEL: {level_instruction}"

    prompt += f"\nCRITERIA TEMPLATE: {criterion_instruction}"
    prompt += f"\n\nCOURSE CONTENT:\n{request.course_input}"

    if request.custom_instructions:
        prompt += f"\n\nADDITIONAL INSTRUCTIONS: {request.custom_instructions}"

    if request.institution:
        prompt += f"\n\nISSUING INSTITUTION: {request.institution}"

    if request.credit_hours > 0:
        prompt += f"\n\nCREDIT HOURS: {request.credit_hours}"

    prompt += '\n\nGenerate Open Badges 3.0 compliant JSON metadata. Return a valid JSON object with exact schema: { "badge_name": "string", "badge_description": "string", "criteria": { "narrative": "string" } }'

    return prompt

def find_balanced_json(text: str) -> Optional[str]:
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

async def call_model_async(prompt: str, timeout_s: float = 300.0) -> str:
    """Call the badge generation model asynchronously."""
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
    
    timeout = httpx.Timeout(timeout_s, read=timeout_s + 30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(OLLAMA_API, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Model server error {resp.status_code}: {resp.text[:200]}")
        
        try:
            response_json = resp.json()
            return response_json.get("response", "") or response_json.get("output", "") or json.dumps(response_json)
        except Exception:
            return resp.text

async def generate_badge_metadata_async(request) -> dict:
    """Generate badge metadata using the model."""
    prompt = build_prompt(request)
    text = await call_model_async(prompt)
    badge_json = extract_json_from_text(text)
    
    if isinstance(badge_json, dict):
        badge_json["_raw_model_output"] = text
    
    return badge_json

# -------------------------
# PYDANTIC MODELS
# -------------------------
class BadgeRequest(BaseModel):
    course_input: str
    badge_style: str = "Professional"
    badge_tone: str = "Authoritative"
    badge_level: Optional[str] = "Intermediate"
    custom_instructions: Optional[str] = ""
    institution: Optional[str] = ""
    credit_hours: int = 0
    criteria_template: str = "Task-Oriented"

class BadgeValidated(BaseModel):
    badge_name: str = Field(..., alias="badge_name")
    badge_description: str = Field(..., alias="badge_description")
    criteria: Dict[str, Any] = Field(default_factory=dict)
    _raw_model_output: str = Field("", alias="_raw_model_output")

# -------------------------
# API ENDPOINTS
# -------------------------
@app.post("/generate_badge")
async def generate_badge(request: BadgeRequest):
    """
    Generate badge metadata only.
    Returns badge metadata and stores it in server history.
    """
    start_time = time.time()
    try:
        # Generate badge JSON from model
        badge_json = await generate_badge_metadata_async(request)

        # Validate using pydantic
        try:
            validated = BadgeValidated(
                badge_name=badge_json.get("badge_name", ""),
                badge_description=badge_json.get("badge_description", ""),
                criteria=badge_json.get("criteria", {}),
                _raw_model_output=badge_json.get("_raw_model_output", "")
            )
        except ValidationError as ve:
            logger.warning("Badge validation failed: %s", ve)
            raise HTTPException(status_code=502, detail=f"Badge schema validation error: {ve}")

        generation_time = time.time() - start_time
        result = {
            "badge_name": validated.badge_name,
            "badge_description": validated.badge_description,
            "criteria": validated.criteria,
        }

        # Store in history
        history_entry = {
            "id": len(badge_history) + 1,
            "timestamp": datetime.now().isoformat(),
            "course_input": (request.course_input[:100] + "...") if len(request.course_input) > 100 else request.course_input,
            "badge_style": request.badge_style,
            "badge_tone": request.badge_tone,
            "criteria_template": request.criteria_template,
            "custom_instructions": request.custom_instructions,
            "badge_level": request.badge_level,
            "institution": request.institution,
            **result
        }
        badge_history.append(history_entry)
        
        # Keep only last 50 entries
        if len(badge_history) > 50:
            badge_history.pop(0)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /generate_badge: %s", e)
        return {"error": "generation_failed", "message": str(e), "generation_time": time.time() - start_time}

@app.get("/badge_history")
async def get_badge_history(limit: int = 20):
    """Get badge generation history."""
    return {
        "history": badge_history[-limit:] if limit > 0 else badge_history,
        "total": len(badge_history)
    }

@app.get("/badge/{badge_id}")
async def get_badge_by_id(badge_id: int):
    """Get specific badge by ID."""
    badge = next((b for b in badge_history if b["id"] == badge_id), None)
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")
    return badge

@app.delete("/badge_history")
async def clear_badge_history():
    """Clear badge history."""
    global badge_history
    badge_history.clear()
    return {"message": "Badge history cleared"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

