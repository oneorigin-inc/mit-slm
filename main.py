from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List, Dict, Any
import httpx
import json
import time
from datetime import datetime
import logging
import re
import asyncio
import random
import uuid

# TF-IDF & cosine similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Text preprocessing
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer
    from nltk.tokenize import word_tokenize
    
    required_downloads = ['punkt', 'stopwords']
    
    for resource in required_downloads:
        try:
            nltk.data.find(f'tokenizers/{resource}' if 'punkt' in resource else f'corpora/{resource}')
        except LookupError:
            print(f"Downloading NLTK resource: {resource}")
            nltk.download(resource, quiet=True)
    
    NLTK_AVAILABLE = True
    STOP_WORDS = set(stopwords.words('english'))
    STEMMER = PorterStemmer()
    print("✓ NLTK initialized successfully")
    
except ImportError:
    NLTK_AVAILABLE = False
    STOP_WORDS = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'])
    print("⚠ NLTK not available, using basic preprocessing")

except Exception as e:
    print(f"⚠ NLTK setup failed: {e}, using basic preprocessing")
    NLTK_AVAILABLE = False
    STOP_WORDS = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'])

# CONFIGURATION
MODEL_CONFIG = {
    "model_name": "phi4_chat_4:latest",
    "temperature": 0.15,
    "top_p": 0.8,
    "top_k": 30,
    "num_predict": 400,
    "repeat_penalty": 1.05,
    "num_ctx": 4096,
    "stop": ["<|end|>", "}\n\n"]
}

OLLAMA_API = "http://localhost:11434/api/generate"

app = FastAPI()
logger = logging.getLogger("uvicorn.error")

# Icons data - will be populated when JSON file is available
ICONS_DATA = []

# Basic icon fallback for when JSON not loaded
ICON_KEYWORDS = {
    "code.png": ["programming", "coding", "software", "development", "script", "algorithm"],
    "atom.png": ["science", "research", "lab", "study", "chemistry", "physics"],
    "leadership.png": ["leadership", "manage", "team", "lead", "guide", "organize"],
    "calculator.png": ["math", "calculate", "number", "statistic", "arithmetic"],
    "color-palette.png": ["art", "design", "creative", "visual", "graphics"],
    "trophy.png": ["achievement", "winner", "champion", "success", "excellence"],
    "graduation-cap.png": ["graduation", "academic", "education", "degree"],
    "brain.png": ["intelligence", "thinking", "cognitive", "psychology"],
    "gear.png": ["engineering", "mechanical", "technical", "system"],
    "shield.png": ["security", "protection", "safety", "cybersecurity"]
}

def load_icons_data(json_file_path: str):
    """Load icons data from JSON file"""
    global ICONS_DATA
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            ICONS_DATA = json.load(f)
        print(f"✓ Loaded {len(ICONS_DATA)} icons from {json_file_path}")
    except FileNotFoundError:
        print(f"⚠ Icons file not found: {json_file_path}, using keyword fallback")
    except json.JSONDecodeError as e:
        print(f"⚠ Invalid JSON in icons file: {e}, using keyword fallback")
    except Exception as e:
        print(f"⚠ Error loading icons: {e}, using keyword fallback")

# Try to load icons on startup (will use fallback if file not found)
load_icons_data("icons.json")

# DESCRIPTIONS AND TEMPLATES
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

# RANDOM PARAMETER SELECTION FUNCTIONS

def get_random_parameters(user_request) -> Dict[str, str]:
    """Generate random parameters, but respect user-provided ones"""
    
    # Get random selections for empty/default parameters
    random_params = {}
    
    # Badge Style - randomly select if not provided or empty
    if not user_request.badge_style or user_request.badge_style.strip() == "":
        random_params['badge_style'] = random.choice(list(STYLE_DESCRIPTIONS.keys()))
    else:
        random_params['badge_style'] = user_request.badge_style
    
    # Badge Tone - randomly select if not provided or empty
    if not user_request.badge_tone or user_request.badge_tone.strip() == "":
        random_params['badge_tone'] = random.choice(list(TONE_DESCRIPTIONS.keys()))
    else:
        random_params['badge_tone'] = user_request.badge_tone
    
    # Criterion Style - randomly select if not provided or empty
    if not user_request.criterion_style or user_request.criterion_style.strip() == "":
        random_params['criterion_style'] = random.choice(list(CRITERION_TEMPLATES.keys()))
    else:
        random_params['criterion_style'] = user_request.criterion_style
    
    # Badge Level - randomly select if not provided or empty
    if not user_request.badge_level or user_request.badge_level.strip() == "":
        random_params['badge_level'] = random.choice(list(LEVEL_DESCRIPTIONS.keys()))
    else:
        random_params['badge_level'] = user_request.badge_level
    
    return random_params

def apply_regeneration_overrides(current_params: Dict[str, str], regeneration_request: Dict[str, str]) -> Dict[str, str]:
    """Override specific parameters for regeneration"""
    updated_params = current_params.copy()
    
    # Override with new random selections for specified parameters
    if "badge_style" in regeneration_request:
        updated_params['badge_style'] = random.choice(list(STYLE_DESCRIPTIONS.keys()))
    
    if "badge_tone" in regeneration_request:
        updated_params['badge_tone'] = random.choice(list(TONE_DESCRIPTIONS.keys()))
    
    if "criterion_style" in regeneration_request:
        updated_params['criterion_style'] = random.choice(list(CRITERION_TEMPLATES.keys()))
    
    if "badge_level" in regeneration_request:
        updated_params['badge_level'] = random.choice(list(LEVEL_DESCRIPTIONS.keys()))
    
    return updated_params

def process_course_input(course_input: str) -> str:
    """Process course input to handle multiple courses or complex content"""
    
    # Check if it contains multiple courses (separated by common delimiters)
    course_separators = ['\n', ';', '|', '&', ' and ', ' + ', '//']
    
    # Count potential separators
    separator_found = None
    for sep in course_separators:
        if sep in course_input and course_input.count(sep) >= 1:
            separator_found = sep
            break
    
    if separator_found:
        courses = [course.strip() for course in course_input.split(separator_found) if course.strip()]
        if len(courses) > 1:
            return f"multiple courses: {', '.join(courses)}"
    
    return course_input

# HELPER FUNCTIONS

def extract_json_from_response(response_text: str) -> dict:
    """Extract JSON from model response, handling various formats."""
    if not response_text or not response_text.strip():
        return {}
    
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON-like content
    json_patterns = [
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
        r'\{.*\}',
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, response_text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
    
    logger.warning("Could not extract valid JSON from response: %s", response_text[:200])
    return {"error": "json_extraction_failed", "raw_response": response_text}

async def call_model_async(prompt: str, config: dict = None) -> str:
    """Make async API call to Ollama."""
    if config is None:
        config = MODEL_CONFIG
    
    payload = {
        "model": config["model_name"],
        "prompt": prompt,
        "temperature": config["temperature"],
        "top_p": config["top_p"],
        "top_k": config["top_k"],
        "num_predict": config["num_predict"],
        "repeat_penalty": config["repeat_penalty"],
        "num_ctx": config["num_ctx"],
        "stop": config["stop"],
        "stream": False
    }
    
    timeout = httpx.Timeout(120.0)
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(OLLAMA_API, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()
    except httpx.TimeoutException:
        logger.error("Model request timed out")
        raise HTTPException(status_code=504, detail="Model request timed out")
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error: %s", e)
        raise HTTPException(status_code=502, detail=f"Model API error: {e}")
    except Exception as e:
        logger.error("Unexpected error calling model: %s", e)
        raise HTTPException(status_code=500, detail=f"Model call failed: {e}")

def preprocess_text(text: str) -> str:
    """Enhanced text preprocessing with improved handling."""
    if not text:
        return ""
    
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    if NLTK_AVAILABLE:
        try:
            tokens = word_tokenize(text)
            tokens = [STEMMER.stem(token) for token in tokens if token not in STOP_WORDS and len(token) > 2]
            return ' '.join(tokens)
        except Exception as e:
            logger.warning("NLTK preprocessing failed: %s", e)
    
    # Basic fallback preprocessing
    words = text.split()
    words = [word for word in words if word not in STOP_WORDS and len(word) > 2]
    return ' '.join(words)

def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate TF-IDF cosine similarity between two texts."""
    if not text1 or not text2:
        return 0.0
    
    try:
        processed_text1 = preprocess_text(text1)
        processed_text2 = preprocess_text(text2)
        
        if not processed_text1 or not processed_text2:
            return 0.0
        
        vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform([processed_text1, processed_text2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        return float(similarity)
    except Exception as e:
        logger.warning("Similarity calculation failed: %s", e)
        return 0.0

# Badge image generation functions
def _rand_hex():
    return "#" + "".join(random.choice("0123456789ABCDEF") for _ in range(6))

def _pick_palette_color(palette):
    if random.random() < 0.7 and palette:
        return random.choice(palette)
    return _rand_hex()

def calculate_font_size(text: str, base_size: int) -> int:
    """Calculate font size based on text length within spec limits"""
    if not text:
        return base_size
    
    # Scale down for longer text, stay within 40-50 range
    if len(text) > 30:
        return max(base_size - 8, 40)
    elif len(text) > 20:
        return max(base_size - 4, 40)
    
    return min(base_size, 50)

def generate_badge_config(
    meta: dict,
    seed: int | None = None,
    logo_path: str = "assets/logos/wgu_logo.png",
):
    """Generate text-based badge configuration following spec"""
    if seed is not None:
        random.seed(seed)

    warm = ["#FF6F61", "#FF8C42", "#FFB703", "#FB8500", "#E76F51", "#D9544D"]
    cool = ["#118AB2", "#06D6A0", "#26547C", "#2A9D8F", "#457B9D", "#00B4D8"]
    neutrals = ["#000000", "#222222", "#333333", "#555555", "#777777", "#999999"]

    # Fixed canvas per spec
    canvas = {"width": 600, "height": 600}

    # Background layer (z: 0-9)
    background_layer = {
        "type": "BackgroundLayer",
        "mode": "solid",
        "color": "#FFFFFF",
        "z": 0,
    }

    # Shape layer (z: 10-19)
    shape = random.choice(["hexagon", "circle", "rounded_rect"])
    
    fill_mode = random.choice(["solid", "gradient"])
    if fill_mode == "solid":
        fill = {
            "mode": "solid",
            "color": _pick_palette_color(warm + cool),
        }
    else:
        start = _pick_palette_color(warm)
        end = _pick_palette_color(cool if random.random() < 0.6 else warm)
        if end == start:
            end = _rand_hex()
        fill = {
            "mode": "gradient",
            "start_color": start,
            "end_color": end,
            "vertical": True,
        }

    # Border (optional per spec)
    if random.random() < 0.6:
        border = {
            "color": _pick_palette_color(neutrals + cool + warm),
            "width": random.randint(1, 6),
        }
    else:
        border = {
            "color": None,
            "width": 0
        }

    # Shape-specific params per spec
    if shape == "hexagon":
        params = {"radius": 250}
    elif shape == "circle":
        params = {"radius": 250}
    else:  # rounded_rect
        params = {
            "radius": random.randint(0, 100),
            "width": 450,
            "height": 450,
        }

    shape_layer = {
        "type": "ShapeLayer",
        "shape": shape,
        "fill": fill,
        "border": border,
        "params": params,
        "z": random.randint(10, 19),
    }

    # Logo layer (z: 20-29)
    logo_layer = {
        "type": "LogoLayer",
        "path": logo_path,
        "size": {"dynamic": True},
        "position": {"x": "center", "y": "dynamic"},
        "z": random.randint(20, 29),
    }

    # Smart text processing - always include subtitle for text layouts
    def _clip_smart(s, max_len=40):
        if not s:
            return ""
        s = str(s).strip()
        if len(s) <= max_len:
            return s
        return s[:max_len-1] + "…"

    title = _clip_smart(meta.get("badge_title") or "Badge Title")
    subtitle = _clip_smart(meta.get("subtitle") or "Certified Achievement")
    extra = _clip_smart(meta.get("extra_text") or "")

    # For text layouts, always include at least title + subtitle
    texts = [title, subtitle]
    if extra and len(title) <= 20 and len(subtitle) <= 20:  # Add third only if others are short
        texts.append(extra)

    # Text layers (z: 30-39)
    text_layers = []
    z_values = sorted(random.sample(range(30, 40), len(texts)))
    
    for idx, txt in enumerate(texts):
        if not txt:
            continue
            
        # Font size within spec (40-50)
        base_size = 48 if idx == 0 else 44 if idx == 1 else 40
        font_size = calculate_font_size(txt, base_size)
        
        color = _pick_palette_color(neutrals if idx == 0 else neutrals + cool + warm)
        
        # Line gap within spec (4-7)
        line_gap = random.randint(4, 7)
        
        text_layer = {
            "type": "TextLayer",
            "text": txt,
            "font": {
                "path": "assets/fonts/ArialBold.ttf" if idx == 0 else "assets/fonts/Arial.ttf",
                "size": font_size,
            },
            "color": color,
            "align": {"x": "center", "y": "dynamic"},
            "wrap": {
                "dynamic": True,
                "line_gap": line_gap,
            },
            "z": z_values[idx],
        }
        text_layers.append(text_layer)

    config = {
        "canvas": canvas,
        "layers": [
            # background_layer,
            shape_layer,
            logo_layer,
            *text_layers,
        ],
    }

    return config

def generate_badge_image_config(
    meta: dict,
    seed: int | None = None,
    icon_dir: str = "assets/icons/",
    suggested_icon: str | None = None,
):
    """Generate icon-based badge configuration"""
    if seed is not None:
        random.seed(seed)

    warm = ["#FF6F61", "#FF8C42", "#FFB703", "#FB8500", "#E76F51", "#D9544D"]
    cool = ["#118AB2", "#06D6A0", "#26547C", "#2A9D8F", "#457B9D", "#00B4D8"]
    neutrals = ["#000000", "#222222", "#333333", "#555555", "#777777", "#999999"]

    if suggested_icon:
        icon_file = suggested_icon
    else:
        icon_file = random.choice(["trophy.png", "goal.png", "solution.png", "diamond.png"])
    
    final_icon_path = icon_dir.rstrip("/") + "/" + icon_file

    canvas = {"width": 600, "height": 600}

    background_layer = {
        "type": "BackgroundLayer",
        "mode": "solid",
        "color": "#FFFFFF",
        "z": 0,
    }

    shape = random.choice(["hexagon", "circle", "rounded_rect"])
    z_shape = random.randint(10, 19)

    fill_mode = random.choice(["solid", "gradient"])
    if fill_mode == "solid":
        fill = {
            "mode": "solid",
            "color": _pick_palette_color(warm + cool)
        }
    else:
        start = _pick_palette_color(warm)
        end = _pick_palette_color(cool if random.random() < 0.6 else warm)
        if end == start:
            end = _rand_hex()
        fill = {
            "mode": "gradient",
            "start_color": start,
            "end_color": end,
            "vertical": True,
        }

    if random.random() < 0.6:
        border = {
            "color": _pick_palette_color(neutrals + cool + warm),
            "width": random.randint(1, 6),
        }
    else:
        border = {"color": None, "width": 0}

    if shape in ("hexagon", "circle"):
        params = {"radius": 250}
    else:
        params = {"radius": random.randint(0, 100), "width": 450, "height": 450}

    shape_layer = {
        "type": "ShapeLayer",
        "shape": shape,
        "fill": fill,
        "border": border,
        "params": params,
        "z": z_shape,
    }

    image_layer = {
        "type": "ImageLayer",
        "path": final_icon_path,
        "size": {"dynamic": True},
        "position": {"x": "center", "y": "center"},
        "z": random.randint(20, 29),
    }

    config = {
        "canvas": canvas,
        "layers": [
            # background_layer,
            shape_layer,
            image_layer
        ],
    }

    return config

async def get_icon_suggestions_for_badge(
    badge_name: str,
    badge_description: str,
    custom_instructions: str = "",
    top_k: int = 3
) -> Dict[str, Any]:
    """Get icon suggestions using TF-IDF similarity when ICONS_DATA is available, else keyword matching"""
    combined_text = f"{badge_name} {badge_description} {custom_instructions}"
    
    if ICONS_DATA:
        # Use TF-IDF similarity with full icon data
        processed_query = preprocess_text(combined_text)
        
        similarities = []
        for icon in ICONS_DATA:
            # Combine description and keywords for matching
            icon_text = f"{icon.get('description', '')} {' '.join(icon.get('keywords', []))}"
            similarity = calculate_similarity(processed_query, icon_text)
            similarities.append({
                "name": icon["name"],
                "display_name": icon.get("display_name", icon["name"]),
                "description": icon.get("description", ""),
                "category": icon.get("category", ""),
                "similarity_score": similarity
            })
        
        # Sort by similarity and get top suggestions
        similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return {
            "suggested_icon": similarities[0] if similarities else {
                "name": "trophy.png", 
                "display_name": "Trophy",
                "description": "Default achievement icon", 
                "similarity_score": 0.5
            },
            "alternatives": similarities[1:top_k] if len(similarities) > 1 else [],
            "matching_method": "tfidf_similarity",
            "total_icons_available": len(ICONS_DATA)
        }
    
    else:
        # Fallback to keyword matching
        combined_text_lower = combined_text.lower()
        
        # Score icons based on keyword matches
        scores = {}
        for icon, keywords in ICON_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in combined_text_lower)
            if score > 0:
                scores[icon] = score
        
        # Get top suggestions
        sorted_icons = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_icons:
            suggested = sorted_icons[0][0]
            alternatives = [{"name": icon, "similarity_score": score/10} for icon, score in sorted_icons[1:top_k]]
        else:
            suggested = "trophy.png"
            alternatives = [{"name": "goal.png", "similarity_score": 0.5}]
        
        return {
            "suggested_icon": {
                "name": suggested,
                "display_name": suggested.replace('.png', '').title(),
                "description": f"Contextually selected icon for {badge_name}",
                "similarity_score": 0.7
            },
            "alternatives": alternatives,
            "matching_method": "keyword_fallback",
            "total_icons_available": len(ICON_KEYWORDS)
        }

async def generate_text_image_config(badge_name: str, badge_description: str, 
                                   image_text: dict, institution: str) -> dict:
    """Generate image configuration with optimized text overlay"""
    seed = random.randint(1, 10000)
    
    meta = {
        "badge_title": image_text.get("short_title", badge_name),
        "subtitle": image_text.get("institution_display", institution),
        "extra_text": image_text.get("achievement_phrase", "Achievement Unlocked")
    }
    
    config = generate_badge_config(
        meta=meta,
        seed=seed,
        logo_path="assets/logos/institution_logo.png"
    )
    
    return {
        "layout_type": "text_overlay",
        "config": config,
        "image_text": image_text,
        "background_style": random.choice(["gradient", "solid", "pattern"]),
        "text_position": random.choice(["center", "bottom", "top"]),
        "color_scheme": random.choice(["professional", "vibrant", "minimal"]),
        "font_style": random.choice(["modern", "classic", "bold"]),
        "seed_used": seed
    }

async def generate_icon_image_config(badge_name: str, badge_description: str, 
                                   icon_suggestions: dict, institution: str) -> dict:
    """Generate image configuration with suggested icon"""
    
    suggested_icon = None
    if icon_suggestions and icon_suggestions.get('suggested_icon', {}).get('name'):
        suggested_icon = icon_suggestions['suggested_icon']['name']
    
    seed = random.randint(1, 10000)
    
    meta = {
        "badge_title": badge_name,
        "subtitle": institution,
        "extra_text": badge_description
    }
    
    config = generate_badge_image_config(
        meta=meta,
        seed=seed,
        suggested_icon=suggested_icon
    )
    
    return {
        "layout_type": "icon_based",
        "config": config,
        "suggested_icon": suggested_icon,
        "seed_used": seed
    }
async def generate_badge_image(image_config: Dict[str, Any]) -> str:
    """Call the image generation API and return base64 image

    TODO: Replace hardcoded localhost:3001 with Docker Compose service URL in production
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:3001/api/v1/badge/generate",
                json=image_config,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result.get("data", {}).get("base64", "")
    except Exception as e:
        logger.error(f"Failed to generate badge image: {e}")
        return ""
async def generate_badge_metadata_async(request) -> dict:
    """Generate badge metadata using enhanced Modelfile system context"""
    
    random_params = get_random_parameters(request)
    processed_course_input = process_course_input(request.course_input)
    
    # Build context-rich user message
    user_content = f"""Course Content: {processed_course_input}

Parameters:
- Style: {STYLE_DESCRIPTIONS.get(random_params['badge_style'])}
- Tone: {TONE_DESCRIPTIONS.get(random_params['badge_tone'])}  
- Level: {LEVEL_DESCRIPTIONS.get(random_params['badge_level'])}
- Criterion Style: {CRITERION_TEMPLATES.get(random_params['criterion_style'])}"""

    if request.institution:
        user_content += f"\n- Institution: {request.institution}"
        
    if request.custom_instructions:
        user_content += f"\n- Special Instructions: {request.custom_instructions}"

    user_content += "\n\nGenerate badge JSON:"

    # Minimal prompt - Modelfile handles all the complex instructions
    prompt = user_content
    
    response = await call_model_async(prompt)
    result = extract_json_from_response(response)
    result["raw_model_output"] = response
    result["selected_parameters"] = random_params
    result["processed_course_input"] = processed_course_input
    
    return result


# PYDANTIC MODELS

class BadgeRequest(BaseModel):
    course_input: str = Field(..., description="Course content or description to generate badge from. Can be multiple courses separated by newlines, semicolons, or 'and'")
    badge_style: str = Field(default="", description="Style of badge generation")
    badge_tone: str = Field(default="", description="Tone for badge content")
    criterion_style: str = Field(default="", description="Style for criteria generation")
    custom_instructions: Optional[str] = Field(default=None, description="Additional custom requirements")
    badge_level: str = Field(default="", description="Badge difficulty level")
    institution: Optional[str] = Field(default=None, description="Issuing institution name")

class RegenerationRequest(BaseModel):
    course_input: str = Field(..., description="Original course content")
    regenerate_parameters: List[str] = Field(..., description="List of parameters to regenerate: ['badge_style', 'badge_tone', 'criterion_style', 'badge_level']")
    custom_instructions: Optional[str] = Field(default=None, description="Additional custom requirements")
    institution: Optional[str] = Field(default=None, description="Issuing institution name")

class BadgeValidated(BaseModel):
    badge_name: str
    badge_description: str  
    criteria: Dict[str, Any]
    raw_model_output: str

class BadgeValidated(BaseModel):
    badge_name: str
    badge_description: str  
    criteria: Dict[str, Any]
    raw_model_output: str

class BadgeResponse(BaseModel):
    credentialSubject: Dict[str, Any]
    imageConfig: Dict[str, Any] 
    badge_id: str

class AppendDataRequest(BaseModel):
    badge_id: int = Field(..., description="Badge ID from history to append data to")
    append_data: Dict[str, Any] = Field(..., description="JSON data to append to the badge result")

# API ENDPOINTS

@app.post("/edit-badge-metadata")
async def edit_badge_metadata(request: AppendDataRequest):
    """Append data to an existing badge result from histo
    ry"""
    try:
        # Find the badge in history by ID
        target_badge = None
        for badge in badge_history:
            if badge.get("id") == request.badge_id:
                target_badge = badge
                break

        if not target_badge:
            raise HTTPException(
                status_code=404,
                detail=f"Badge with ID {request.badge_id} not found in history"
            )

        # Get the existing result
        existing_result = target_badge.get("result")
        if not existing_result:
            raise HTTPException(
                status_code=400,
                detail=f"Badge with ID {request.badge_id} has no result data to append to"
            )

        # Convert existing result to dict if it's a Pydantic model
        if hasattr(existing_result, 'dict'):
            result_dict = existing_result.dict()
        elif hasattr(existing_result, '__dict__'):
            result_dict = existing_result.__dict__
        else:
            result_dict = dict(existing_result) if isinstance(existing_result, dict) else {}

        # Append the new data to badge_data
        updated_result = result_dict.copy()
        if 'badge_data' in updated_result:
            updated_result['badge_data'].update(request.append_data)
        else:
            # Fallback if badge_data doesn't exist
            updated_result.update(request.append_data)

        # Update the badge history entry with the new result
        target_badge["result"] = updated_result
        #target_badge["last_updated"] = datetime.now().isoformat()

        return {
            "message": f"Data successfully appended to badge {request.badge_id}",
            "badge_id": request.badge_id,
            "updated_result": updated_result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /edit_badge_metadata: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to append data: {str(e)}")

@app.post("/optimize_badge_text")
async def optimize_badge_text(badge_data: dict, max_title_chars: int = 25):
    """Optimize badge text for image overlay"""
    prompt = f"""Badge: "{badge_data['badge_name']}"
Description: "{badge_data['badge_description']}"
Institution: "{badge_data.get('institution', '')}"

Generate optimized text for image overlay:
- Short title (max {max_title_chars} chars)
- Brief description (1-2 lines)
- Institution display name
- Key achievement phrase

Return JSON format:
{{
    "short_title": "condensed badge name",
    "brief_description": "one line summary",
    "institution_display": "institution name",
    "achievement_phrase": "motivational phrase"
}}"""

    response = await call_model_async(prompt)
    return extract_json_from_response(response)

@app.post("/generate-badge-suggestions", response_model=BadgeResponse)
async def generate_badge(request: BadgeRequest):
    """Generate a single badge with random parameter selection"""
    start_time = time.time()
    try:
        # Generate badge metadata with random parameters
        badge_json = await generate_badge_metadata_async(request)

        try:
            validated = BadgeValidated(
                badge_name=badge_json.get("badge_name", ""),
                badge_description=badge_json.get("badge_description", ""),
                criteria=badge_json.get("criteria", {}),  # This already contains {"narrative": "string"}
                raw_model_output=badge_json.get("raw_model_output", "")
            )
        except ValidationError as ve:
            logger.warning("Badge validation failed: %s", ve)
            raise HTTPException(status_code=502, detail=f"Badge schema validation error: {ve}")

        # Generate image configuration with random selection
        image_type = random.choice(["text_overlay", "icon_based"])
        logger.info(f"Selected image type: {image_type}")

        if image_type == "icon_based":
            icon_suggestions = await get_icon_suggestions_for_badge(
                badge_name=validated.badge_name,
                badge_description=validated.badge_description,
                custom_instructions=request.custom_instructions or "",
                top_k=3
            )
            
            image_config_wrapper = await generate_icon_image_config(
                validated.badge_name,
                validated.badge_description,
                icon_suggestions,
                request.institution or ""
            )
            
            image_config = image_config_wrapper.get("config", {})
            
        else:  # text_overlay
            optimized_text = await optimize_badge_text({
                "badge_name": validated.badge_name,
                "badge_description": validated.badge_description,
                "institution": request.institution or ""
            })
            
            image_config_wrapper = await generate_text_image_config(
                validated.badge_name,
                validated.badge_description,
                optimized_text,
                request.institution or ""
            )
            
            image_config = image_config_wrapper.get("config", {})

        # Generate badge image
        image_base64 = await generate_badge_image(image_config)

        # Generate badge ID
        badge_id = str(uuid.uuid4())

        # Create the response using your existing Pydantic model structure
        result = BadgeResponse(
            credentialSubject={
                "achievement": {
                    "criteria": validated.criteria,  # This is already {"narrative": "string"} format
                    "description": validated.badge_description,
                    "image": {
                        "id": f"https://example.com/achievements/badge_{badge_id}/image",
                        "image_base64": image_base64
                    },
                    "name": validated.badge_name
                }
            },
            imageConfig=image_config,
            badge_id=str(badge_id)  # Convert to string as expected by your model
        )

        # Store in history with the full result for editing capability
        history_entry = {
            "id": len(badge_history) + 1,
            "timestamp": datetime.now().isoformat(),
            "course_input": (request.course_input[:100] + "...") if len(request.course_input) > 100 else request.course_input,
            "processed_course_input": badge_json.get("processed_course_input", request.course_input),
            "user_badge_style": request.badge_style,
            "user_badge_tone": request.badge_tone,
            "user_criterion_style": request.criterion_style,
            "user_badge_level": request.badge_level,
            "custom_instructions": request.custom_instructions,
            "institution": request.institution,
            "selected_image_type": image_type,
            "selected_parameters": badge_json.get("selected_parameters", {}),
            "result": result,  # Store the full result for editing
            "generation_time": time.time() - start_time
        }
        badge_history.append(history_entry)
        
        if len(badge_history) > 50:
            badge_history.pop(0)

        selected_params = badge_json.get("selected_parameters", {})
        logger.info(f"Generated badge ID {badge_id}: '{validated.badge_name}' with parameters: {selected_params}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /generate-badge-suggestions: %s", e)
        raise HTTPException(status_code=500, detail=f"Badge generation error: {str(e)}")


@app.post("/regenerate_badge", response_model=BadgeResponse)
async def regenerate_badge(request: RegenerationRequest):
    """Regenerate badge with specific parameter overrides"""
    start_time = time.time()
    try:
        # Create a mock request object for consistency
        mock_request = BadgeRequest(
            course_input=request.course_input,
            badge_style="",  # Will be randomly overridden
            badge_tone="",   # Will be randomly overridden
            criterion_style="",  # Will be randomly overridden
            badge_level="",  # Will be randomly overridden
            custom_instructions=request.custom_instructions,
            institution=request.institution
        )
        
        # Get current random parameters
        current_params = get_random_parameters(mock_request)
        
        # Apply regeneration overrides
        regeneration_map = {param: True for param in request.regenerate_parameters}
        updated_params = apply_regeneration_overrides(current_params, regeneration_map)
        
        # Update mock request with new parameters
        mock_request.badge_style = updated_params['badge_style']
        mock_request.badge_tone = updated_params['badge_tone']
        mock_request.criterion_style = updated_params['criterion_style']
        mock_request.badge_level = updated_params['badge_level']
        
        # Generate badge with updated parameters
        badge_json = await generate_badge_metadata_async(mock_request)

        try:
            validated = BadgeValidated(
                badge_name=badge_json.get("badge_name", ""),
                badge_description=badge_json.get("badge_description", ""),
                criteria=badge_json.get("criteria", {}),
                raw_model_output=badge_json.get("raw_model_output", "")
            )
        except ValidationError as ve:
            logger.warning("Badge validation failed: %s", ve)
            raise HTTPException(status_code=502, detail=f"Badge schema validation error: {ve}")

        # Generate image configuration
        image_type = random.choice(["text_overlay", "icon_based"])
        
        if image_type == "icon_based":
            icon_suggestions = await get_icon_suggestions_for_badge(
                badge_name=validated.badge_name,
                badge_description=validated.badge_description,
                custom_instructions=request.custom_instructions or "",
                top_k=3
            )
            
            image_config_wrapper = await generate_icon_image_config(
                validated.badge_name,
                validated.badge_description,
                icon_suggestions,
                request.institution or ""
            )
            
            image_config = image_config_wrapper.get("config", {})
            
        else:  # text_overlay
            optimized_text = await optimize_badge_text({
                "badge_name": validated.badge_name,
                "badge_description": validated.badge_description,
                "institution": request.institution or ""
            })
            
            image_config_wrapper = await generate_text_image_config(
                validated.badge_name,
                validated.badge_description,
                optimized_text,
                request.institution or ""
            )
            
            image_config = image_config_wrapper.get("config", {})

        # Format criteria as string
        criteria_text = ""
        if isinstance(validated.criteria, dict):
            criteria_parts = []
            for key, value in validated.criteria.items():
                if isinstance(value, list):
                    criteria_parts.append(f"{key}: {'; '.join(value)}")
                else:
                    criteria_parts.append(f"{key}: {value}")
            criteria_text = " | ".join(criteria_parts)
        else:
            criteria_text = str(validated.criteria)

        # Create the response using Pydantic models
        result = BadgeResponse(
            badge_data=BadgeData(
                name=validated.badge_name,
                description=validated.badge_description,
                criteria=criteria_text
            ),
            badge_image_data=BadgeImageData(
                imageConfig=image_config,
                image_base64=None  # Placeholder for future base64 image data
            )
        )

        logger.info(f"Regenerated badge with overridden parameters: {request.regenerate_parameters}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /regenerate_badge: %s", e)
        raise HTTPException(status_code=500, detail=f"Badge regeneration error: {str(e)}")

@app.get("/badge_history")
async def get_badge_history():
    """Get the recent badge generation history."""
    return {"history": badge_history, "total_count": len(badge_history)}

@app.delete("/badge_history")
async def clear_badge_history():
    """Clear the badge generation history."""
    global badge_history
    badge_history.clear() 
    return {"message": "Badge history cleared successfully"}

@app.get("/styles")
async def get_styles():
    """Get available badge styles and their descriptions."""
    return {
        "badge_styles": STYLE_DESCRIPTIONS,
        "badge_tones": TONE_DESCRIPTIONS,
        "criterion_styles": CRITERION_TEMPLATES,
        "badge_levels": LEVEL_DESCRIPTIONS
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
