from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List, Dict, Any
import json
import time
from datetime import datetime
import logging
import re
import asyncio
import random

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

# LangChain LlamaCpp setup
try:
    from langchain_community.llms import LlamaCpp
    from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler
    LANGCHAIN_LLAMACPP_AVAILABLE = True
    print("✓ LangChain LlamaCpp available")
except ImportError:
    LANGCHAIN_LLAMACPP_AVAILABLE = False
    print("⚠ LangChain LlamaCpp not available - install with: pip install langchain-community")

# GPU Detection
def check_gpu_availability():
    """Check if CUDA is available through multiple methods"""
    cuda_available = False
    gpu_info = {"method": "none", "details": ""}
    
    # Method 1: Check PyTorch CUDA availability
    try:
        import torch
        if torch.cuda.is_available():
            cuda_available = True
            gpu_info = {
                "method": "torch",
                "details": f"CUDA devices: {torch.cuda.device_count()}, "
                         f"Current device: {torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else 'None'}"
            }
            print(f"✓ CUDA detected via PyTorch: {gpu_info['details']}")
            return cuda_available, gpu_info
    except ImportError:
        print("⚠ PyTorch not available for CUDA detection")
    
    # Method 2: Check NVIDIA-SMI availability
    try:
        import subprocess
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            cuda_available = True
            gpu_info = {
                "method": "nvidia_smi",
                "details": "NVIDIA GPU driver detected"
            }
            print("✓ CUDA detected via nvidia-smi")
            return cuda_available, gpu_info
    except Exception as e:
        print(f"⚠ nvidia-smi check failed: {e}")
    
    print("ℹ No CUDA support detected, will use CPU-only mode")
    return cuda_available, gpu_info

# Check GPU availability at startup
CUDA_AVAILABLE, GPU_INFO = check_gpu_availability()

# CONFIGURATION
MODEL_CONFIG = {
    "model_path": "gguf/Phi-4-mini-instruct_Q4_K_M.gguf",
    "temperature": 0.15,
    "top_p": 0.8,
    "top_k": 30,
    "max_tokens": 400,
    "repeat_penalty": 1.05,
    "n_ctx": 4096,
    "stop": ["<|end|>", "}\n\n"],
    "n_gpu_layers": -1 if CUDA_AVAILABLE else 0,
    "verbose": False,
    "streaming": False
}

app = FastAPI()
logger = logging.getLogger("uvicorn.error")

# Global model instance
llama_model = None

def initialize_llama_model():
    """Initialize LangChain LlamaCpp model with GPU/CPU detection"""
    global llama_model
    
    if not LANGCHAIN_LLAMACPP_AVAILABLE:
        print("❌ langchain-community not installed. Install with: pip install langchain-community")
        return False
    
    try:
        n_gpu_layers = MODEL_CONFIG["n_gpu_layers"] if CUDA_AVAILABLE else 0
        n_batch = 512 if CUDA_AVAILABLE else 256
        
        device_type = "GPU" if CUDA_AVAILABLE else "CPU"
        print(f"Initializing LangChain model with {device_type} ({n_gpu_layers} GPU layers)")
        
        callback_manager = None
        if MODEL_CONFIG.get("streaming", False):
            callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
        
        llama_model = LlamaCpp(
            model_path=MODEL_CONFIG["model_path"],
            n_ctx=MODEL_CONFIG["n_ctx"],
            n_gpu_layers=n_gpu_layers,
            verbose=MODEL_CONFIG["verbose"],
            callback_manager=callback_manager,
            n_batch=n_batch,
            n_threads=None,
            use_mmap=True,
            use_mlock=False,
            temperature=MODEL_CONFIG["temperature"],
            top_p=MODEL_CONFIG["top_p"],
            top_k=MODEL_CONFIG["top_k"],
            max_tokens=MODEL_CONFIG["max_tokens"],
            repeat_penalty=MODEL_CONFIG["repeat_penalty"],
            stop=MODEL_CONFIG["stop"]
        )
        
        print(f"✓ LangChain model initialized on {device_type}")
        return True
        
    except FileNotFoundError:
        print(f"❌ Model file not found: {MODEL_CONFIG['model_path']}")
        return False
    except Exception as e:
        print(f"❌ Failed to initialize model: {e}")
        
        if CUDA_AVAILABLE:
            print("🔄 Attempting CPU fallback...")
            try:
                llama_model = LlamaCpp(
                    model_path=MODEL_CONFIG["model_path"],
                    n_ctx=MODEL_CONFIG["n_ctx"],
                    n_gpu_layers=0,
                    n_batch=256,
                    verbose=MODEL_CONFIG["verbose"],
                    temperature=MODEL_CONFIG["temperature"],
                    top_p=MODEL_CONFIG["top_p"],
                    top_k=MODEL_CONFIG["top_k"],
                    max_tokens=MODEL_CONFIG["max_tokens"],
                    repeat_penalty=MODEL_CONFIG["repeat_penalty"],
                    stop=MODEL_CONFIG["stop"]
                )
                print("✓ CPU fallback successful")
                return True
            except Exception as cpu_error:
                print(f"❌ CPU fallback failed: {cpu_error}")
        
        return False

# Initialize model on startup
model_initialized = initialize_llama_model()

# Icons data with theme-based mapping
ICONS_DATA = [
    {
      "name": "atom.png",
      "display_name": "Atom",
      "category": "science",
      "description": "Represents scientific knowledge, chemistry, physics, molecular studies, research, scientific discovery, and STEM education",
      "keywords": ["science", "chemistry", "physics", "STEM", "molecular", "research", "atomic", "nuclear"],
      "use_cases": [
        "Science achievement badges",
        "Chemistry course completion",
        "Physics excellence",
        "Research participation",
          "Lab work proficiency"
      ]
    },
    {
      "name": "binary-code.png",
      "display_name": "Binary Code",
      "category": "technology",
      "description": "Represents computer science, programming, digital literacy, coding skills, binary systems, and computational thinking",
      "keywords": ["programming", "coding", "computer science", "binary", "digital", "technology", "software"],
      "use_cases": [
        "Programming course completion",
        "Coding bootcamp achievement",
        "Computer science excellence",
        "Digital literacy milestone",
        "Software development skills"
      ]
    },
    {
      "name": "code.png",
      "display_name": "Code",
      "category": "technology",
      "description": "Represents software development, programming proficiency, coding skills, and technical expertise",
      "keywords": ["programming", "software", "development", "coding", "script", "algorithm", "function"],
      "use_cases": [
        "Software engineering achievement",
        "Algorithm mastery",
        "Code quality excellence",
        "Programming contest winner",
        "Technical skills certification"
      ]
    },
    {
      "name": "brain.png",
      "display_name": "Brain",
      "category": "cognitive",
      "description": "Represents intelligence, critical thinking, cognitive skills, neuroscience, psychology, mental agility, and learning ability",
      "keywords": ["intelligence", "thinking", "cognitive", "psychology", "neuroscience", "mental", "learning", "knowledge"],
      "use_cases": [
        "Critical thinking achievement",
        "Psychology course completion",
        "Neuroscience studies",
        "Problem-solving excellence",
        "Mental math champion"
      ]
    },
    {
      "name": "trophy.png",
      "display_name": "Trophy",
      "category": "achievement",
      "description": "Represents victory, championship, first place, competition winner, and ultimate achievement",
      "keywords": ["trophy", "winner", "champion", "victory", "first", "competition", "prize", "tournament"],
      "use_cases": [
        "Competition winner",
        "Championship trophy",
        "First place achievement",
        "Tournament victor",
        "Grand prize winner"
      ]
    },
    {
      "name": "leadership.png",
      "display_name": "Leadership",
      "category": "leadership",
      "description": "Represents leadership skills, management, strategic thinking, team building, and organizational development",
      "keywords": ["leadership", "management", "strategic", "team", "organization", "executive", "director"],
      "use_cases": [
        "Leadership development",
        "Management training",
        "Strategic planning",
        "Team leadership",
        "Executive skills"
      ]
    }
]

# Color schemes for badge themes
COLOR_SCHEMES = {
    "science": ["#06D6A0", "#26A69A", "#0077BE", "#4CAF50"],
    "technology": ["#FF6B35", "#F7931E", "#3F51B5", "#2196F3"],
    "cognitive": ["#9C27B0", "#673AB7", "#E91E63", "#FF5722"],
    "achievement": ["#FFD700", "#FFC107", "#FF9800", "#795548"],
    "leadership": ["#06D6A0", "#4CAF50", "#2E7D32", "#1B5E20"],
    "default": ["#06D6A0", "#2196F3", "#9C27B0", "#FF6B35"]
}

ICON_KEYWORDS = {
    "code.png": ["programming", "coding", "software", "development", "script", "algorithm"],
    "atom.png": ["science", "research", "lab", "study", "chemistry", "physics"],
    "brain.png": ["intelligence", "thinking", "cognitive", "psychology"],
    "trophy.png": ["achievement", "winner", "champion", "success", "excellence"],
    "leadership.png": ["leadership", "management", "strategic", "team", "organization"]
}

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

# HELPER FUNCTIONS
def get_random_parameters(user_request) -> Dict[str, str]:
    """Generate random parameters, but respect user-provided ones"""
    random_params = {}
    
    if not user_request.badge_style or user_request.badge_style.strip() == "":
        random_params['badge_style'] = random.choice(list(STYLE_DESCRIPTIONS.keys()))
    else:
        random_params['badge_style'] = user_request.badge_style
    
    if not user_request.badge_tone or user_request.badge_tone.strip() == "":
        random_params['badge_tone'] = random.choice(list(TONE_DESCRIPTIONS.keys()))
    else:
        random_params['badge_tone'] = user_request.badge_tone
    
    if not user_request.criterion_style or user_request.criterion_style.strip() == "":
        random_params['criterion_style'] = random.choice(list(CRITERION_TEMPLATES.keys()))
    else:
        random_params['criterion_style'] = user_request.criterion_style
    
    if not user_request.badge_level or user_request.badge_level.strip() == "":
        random_params['badge_level'] = random.choice(list(LEVEL_DESCRIPTIONS.keys()))
    else:
        random_params['badge_level'] = user_request.badge_level
    
    return random_params

def process_course_input(course_input: str) -> str:
    """Process course input to handle multiple courses or complex content"""
    course_separators = ['\n', ';', '|', '&', ' and ', ' + ', '//']
    
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

def select_icon_and_color(course_input: str, badge_name: str) -> tuple:
    """Select appropriate icon and color scheme based on course content"""
    # Combine course input and badge name for analysis
    combined_text = f"{course_input} {badge_name}".lower()
    
    # Calculate similarity scores for each icon
    best_icon = "leadership.png"  # default
    best_score = 0.0
    best_category = "leadership"
    
    for icon_data in ICONS_DATA:
        icon_keywords = " ".join(icon_data["keywords"])
        similarity = calculate_similarity(combined_text, icon_keywords)
        
        if similarity > best_score:
            best_score = similarity
            best_icon = icon_data["name"]
            best_category = icon_data["category"]
    
    # Get color scheme for the category
    colors = COLOR_SCHEMES.get(best_category, COLOR_SCHEMES["default"])
    selected_color = random.choice(colors)
    
    return best_icon, selected_color, best_category

def extract_json_from_response(response_text: str) -> dict:
    """Extract JSON from model response, handling various formats."""
    if not response_text or not response_text.strip():
        return {}
    
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass
    
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
    """Make async call to LangChain LlamaCpp model"""
    global llama_model
    
    if not model_initialized or llama_model is None:
        raise HTTPException(status_code=503, detail="Model not initialized")
    
    try:
        def _call_model():
            return llama_model.invoke(prompt)
        
        loop = asyncio.get_event_loop()
        response_text = await loop.run_in_executor(None, _call_model)
        
        if not response_text or not response_text.strip():
            raise HTTPException(status_code=502, detail="Model returned empty response")
            
        return response_text.strip()
        
    except Exception as e:
        logger.error("LangChain model call failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Model generation error: {str(e)}")

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

async def generate_badge_metadata_async(request) -> dict:
    """Generate badge metadata with random parameter selection"""
    random_params = get_random_parameters(request)
    processed_course_input = process_course_input(request.course_input)
    
    style_desc = STYLE_DESCRIPTIONS.get(random_params['badge_style'], "Use clear, comprehensive language with specific examples.")
    tone_desc = TONE_DESCRIPTIONS.get(random_params['badge_tone'], "Professional and engaging tone.")
    level_desc = LEVEL_DESCRIPTIONS.get(random_params['badge_level'], "Appropriate for learners with basic knowledge.")
    criterion_desc = CRITERION_TEMPLATES.get(random_params['criterion_style'], "Clear, actionable criteria.")
    
    # Separate instruction prompts
    name_instruction = f"""Generate a creative and memorable badge name that captures the essence of the course(s). 
    For multiple courses, create a unifying theme. Emphasize the {random_params['badge_level']} level in the name. 
    Keep it concise but impactful."""
    
    desc_instruction = f"""Provide a comprehensive description covering:
    - Competencies mastered and skills developed
    - Technical tools and technologies used
    - Real-world applications and career relevance
    - Assessment rigor and learning outcomes
    - Employer value and transferable skills
    - Integration of all subject areas cohesively (if multiple courses)
    Emphasize this is {random_params['badge_level']} level content."""
    
    criteria_instruction = f"""Analyze the course content provided and suggest specific criteria based on what's actually covered. Consider these aspects:
    - Assessment methods and evaluation criteria (e.g., quizzes, projects, peer reviews with rubrics) - identify what assessment types would fit this content
    - Practical experiences and hands-on components (e.g., labs, simulations, real-world tasks) - determine what practical work this course would include
    - Collaboration and teamwork expectations (e.g., group projects, discussions) - assess if the content requires collaborative learning
    - Application of knowledge in real-world scenarios (e.g., case studies, internships) - identify relevant real-world applications for this subject matter
    - Integration of multiple subject areas if applicable (e.g., interdisciplinary projects) - note any cross-disciplinary connections in the content
    - Clear, measurable actions using verbs like "demonstrate," "apply," "analyze," "create" - specify concrete actions learners must perform
    - Evidence standards and performance indicators (e.g., proficiency levels, mastery demonstrations) - define what mastery looks like for this content
    - Portfolio requirements or project deliverables - suggest appropriate artifacts students should create
    - Skill demonstration requirements that span all course content - identify key competencies that need demonstration
    - Novel criterion innovations - propose new, creative assessment methods specifically tailored to this content that go beyond traditional approaches
    - Industry-specific standards - suggest criteria that align with current professional practices in the field
    - Technology integration requirements - identify digital tools and platforms that should be mastered for this subject area

    Base your criteria suggestions on actual course content analysis, not generic templates. Create innovative, content-specific criteria that reflect modern learning needs."""
    
    institution_instruction = ""
    if request.institution:
        institution_instruction = f"Highlight that this badge is issued by {request.institution} and emphasize the institution's credibility and standards."
    
    custom_instruction = ""
    if request.custom_instructions:
        custom_instruction = f"Additional focus: {request.custom_instructions}. Follow these instructions and generate badge data accordingly."
    
    system_msg = "You are a badge metadata generator. Return only valid JSON with exact schema: {\"badge_name\": \"string\", \"badge_description\": \"string\", \"criteria\": {\"narrative\": \"string\"}}"
    
    user_content = f"""Create a unique badge for: {processed_course_input}

IMPORTANT: If this covers multiple courses or complex content, create comprehensive content that encompasses all areas while maintaining focus and clarity.

Style Guidelines: {style_desc}
Tone Guidelines: {tone_desc}
Level: {random_params['badge_level']} - {level_desc}
Criterion Format: {criterion_desc}

BADGE NAME INSTRUCTIONS:
{name_instruction}

BADGE DESCRIPTION INSTRUCTIONS:
{desc_instruction}

CRITERIA INSTRUCTIONS:
{criteria_instruction}

{institution_instruction}

{custom_instruction}"""

    prompt = f"<|system|>{system_msg}<|end|>\n<|user|>{user_content}<|end|>\n<|assistant|>"
    
    response = await call_model_async(prompt)
    result = extract_json_from_response(response)
    result["raw_model_output"] = response
    result["selected_parameters"] = random_params
    result["processed_course_input"] = processed_course_input
    
    return result

# PYDANTIC MODELS
class BadgeRequest(BaseModel):
    course_input: str = Field(..., description="Course content or description to generate badge from")
    badge_style: str = Field(default="", description="Style of badge generation")
    badge_tone: str = Field(default="", description="Tone for badge content")
    criterion_style: str = Field(default="", description="Style for criteria generation")
    custom_instructions: Optional[str] = Field(default=None, description="Additional custom requirements")
    badge_level: str = Field(default="", description="Badge difficulty level")
    institution: Optional[str] = Field(default=None, description="Issuing institution name")

class BadgeValidated(BaseModel):
    badge_name: str
    badge_description: str  
    criteria: Dict[str, Any]
    raw_model_output: str

class BadgeResponse(BaseModel):
    credentialSubject: Dict[str, Any]
    imageConfig: Dict[str, Any] 
    badge_id: int

# API ENDPOINTS
@app.post("/generate-badge-suggestions", response_model=BadgeResponse)
async def generate_badge(request: BadgeRequest):
    """Generate a single badge with random parameter selection"""
    start_time = time.time()
    try:
        badge_json = await generate_badge_metadata_async(request)

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

        badge_id = random.randint(100000, 999999)
        
        # Select appropriate icon and color based on course content
        selected_icon, selected_color, category = select_icon_and_color(
            request.course_input, 
            validated.badge_name
        )

        # Create the specific imageConfig structure matching your requirements
        image_config = {
            "canvas": {
                "width": 600,
                "height": 600
            },
            "layers": [
                {
                    "type": "BackgroundLayer",
                    "mode": "solid",
                    "color": "#FFFFFF",
                    "z": 0
                },
                {
                    "type": "ShapeLayer",
                    "shape": "circle",
                    "fill": {
                        "mode": "solid",
                        "color": selected_color
                    },
                    "border": {
                        "color": None,
                        "width": 0
                    },
                    "params": {
                        "radius": 250
                    },
                    "z": 11
                },
                {
                    "type": "ImageLayer",
                    "path": f"../assets/icons/{selected_icon}",
                    "size": {
                        "dynamic": True
                    },
                    "position": {
                        "x": "center",
                        "y": "center"
                    },
                    "z": 21
                }
            ]
        }

        result = BadgeResponse(
            credentialSubject={
                "achievement": {
                    "criteria": validated.criteria,
                    "description": validated.badge_description,
                    "image": {
                        "id": f"https://example.com/achievements/badge_{badge_id}/image",
                        "image_base64": None
                    },
                    "name": validated.badge_name
                }
            },
            imageConfig=image_config,
            badge_id=badge_id
        )

        # Store in history
        history_entry = {
            "id": len(badge_history) + 1,
            "timestamp": datetime.now().isoformat(),
            "course_input": (request.course_input[:100] + "...") if len(request.course_input) > 100 else request.course_input,
            "processed_course_input": badge_json.get("processed_course_input", request.course_input),
            "selected_parameters": badge_json.get("selected_parameters", {}),
            "selected_icon": selected_icon,
            "selected_color": selected_color,
            "selected_category": category,
            "badge_id": badge_id,
            "result": result,
            "generation_time": time.time() - start_time
        }
        badge_history.append(history_entry)
        
        if len(badge_history) > 50:
            badge_history.pop(0)

        selected_params = badge_json.get("selected_parameters", {})
        logger.info(f"Generated badge ID {badge_id}: '{validated.badge_name}' with icon {selected_icon} and color {selected_color}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /generate-badge-suggestions: %s", e)
        raise HTTPException(status_code=500, detail=f"Badge generation error: {str(e)}")

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

@app.get("/icons")
async def get_icons():
    """Get available icons and their categories."""
    return {
        "icons": ICONS_DATA,
        "color_schemes": COLOR_SCHEMES
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    model_status = "initialized" if model_initialized and llama_model is not None else "not_initialized"
    device_info = "GPU" if CUDA_AVAILABLE and MODEL_CONFIG.get("n_gpu_layers", 0) > 0 else "CPU"
    
    return {
        "status": "healthy",
        "model_status": model_status,
        "device": device_info,
        "cuda_available": CUDA_AVAILABLE,
        "gpu_info": GPU_INFO,
        "langchain_llamacpp_available": LANGCHAIN_LLAMACPP_AVAILABLE,
        "nltk_available": NLTK_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/model-info")
async def get_model_info():
    """Get detailed model information and configuration."""
    if not model_initialized or llama_model is None:
        return {
            "initialized": False,
            "error": "Model not initialized",
            "config": MODEL_CONFIG
        }
    
    try:
        model_info = {
            "initialized": True,
            "model_path": MODEL_CONFIG["model_path"],
            "n_ctx": MODEL_CONFIG["n_ctx"],
            "n_gpu_layers": MODEL_CONFIG.get("n_gpu_layers", 0),
            "config": MODEL_CONFIG,
            "framework": "LangChain LlamaCpp"
        }
        
        try:
            import torch
            if torch.cuda.is_available():
                model_info["cuda_available"] = True
                model_info["gpu_count"] = torch.cuda.device_count()
                model_info["gpu_names"] = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
            else:
                model_info["cuda_available"] = False
        except ImportError:
            model_info["cuda_available"] = "unknown (PyTorch not available)"
        
        return model_info
        
    except Exception as e:
        return {
            "initialized": True,
            "error": f"Could not get model info: {str(e)}",
            "config": MODEL_CONFIG
        }

@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    if not model_initialized:
        logger.warning("Model failed to initialize during startup")
    else:
        logger.info("Badge generator service started successfully")

if __name__ == "__main__":
    import uvicorn
    
    if not model_initialized:
        print("\n" + "="*60)
        print("⚠ WARNING: Model not initialized!")
        print("Please ensure:")
        print("1. langchain-community is installed: pip install langchain-community")
        print("2. Model file exists at:", MODEL_CONFIG["model_path"])
        print("3. Model file is in GGUF format")
        print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
