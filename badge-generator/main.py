# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List, Dict, Any
import httpx
import json
import time
from datetime import datetime
import logging
import re
import string

# TF-IDF & cosine similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Text preprocessing (optional - install with: pip install nltk)
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer
    from nltk.tokenize import word_tokenize
    
    # Download required NLTK data (run once)
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
    
    NLTK_AVAILABLE = True
    STOP_WORDS = set(stopwords.words('english'))
    STEMMER = PorterStemmer()
except ImportError:
    NLTK_AVAILABLE = False
    STOP_WORDS = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'])

app = FastAPI()
logger = logging.getLogger("uvicorn.error")

# -------------------------
# ICONS_DATA
# -------------------------
ICONS_DATA =  [
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
      "name": "brackets.png",
      "display_name": "Code Brackets",
      "category": "technology",
      "description": "Represents coding, programming languages, software development, syntax mastery, and technical skills",
      "keywords": ["code", "programming", "development", "syntax", "HTML", "JavaScript", "coding"],
      "use_cases": [
        "Web development achievement",
        "Programming language mastery",
        "Code review excellence",
        "Syntax proficiency",
        "Developer certification"
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
      "name": "calculator.png",
      "display_name": "Calculator",
      "category": "mathematics",
      "description": "Represents mathematical skills, calculation proficiency, accounting, statistics, numerical analysis, and quantitative reasoning",
      "keywords": ["math", "calculation", "numbers", "accounting", "statistics", "arithmetic", "algebra", "finance"],
      "use_cases": [
        "Mathematics achievement",
        "Accounting certification",
        "Statistics mastery",
        "Financial literacy",
        "Arithmetic excellence"
      ]
    },
    {
      "name": "checkmark.png",
      "display_name": "Checkmark",
      "category": "achievement",
      "description": "Represents completion, success, verification, quality assurance, task accomplishment, and goal achievement",
      "keywords": ["complete", "done", "success", "verified", "achieved", "finished", "approved", "passed"],
      "use_cases": [
        "Course completion",
        "Task achievement",
        "Quality verification",
        "Test passed",
        "Requirement fulfilled"
      ]
    },
    {
      "name": "clock.png",
      "display_name": "Clock",
      "category": "skills",
      "description": "Represents time management, punctuality, deadline achievement, scheduling skills, and efficiency",
      "keywords": ["time", "management", "punctual", "deadline", "schedule", "timely", "efficient", "duration"],
      "use_cases": [
        "Time management excellence",
        "Perfect attendance",
        "Deadline achievement",
        "Punctuality award",
        "Speed completion bonus"
      ]
    },
    {
      "name": "cloud-service.png",
      "display_name": "Cloud Service",
      "category": "technology",
      "description": "Represents cloud computing, online services, digital storage, SaaS platforms, and modern IT infrastructure",
      "keywords": ["cloud", "computing", "storage", "online", "SaaS", "AWS", "Azure", "infrastructure"],
      "use_cases": [
        "Cloud computing certification",
        "AWS/Azure proficiency",
        "Online collaboration",
        "Digital transformation",
        "Cloud architecture skills"
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
      "name": "color-palette.png",
      "display_name": "Color Palette",
      "category": "creative",
      "description": "Represents artistic skills, design thinking, creativity, visual arts, color theory, and aesthetic sense",
      "keywords": ["art", "design", "creative", "colors", "painting", "visual", "aesthetic", "graphics"],
      "use_cases": [
        "Art class achievement",
        "Design course completion",
        "Creative excellence",
        "Visual arts mastery",
        "Graphic design certification"
      ]
    },
    {
      "name": "crown.png",
      "display_name": "Crown",
      "category": "achievement",
      "description": "Represents leadership, excellence, top performance, mastery, championship, and highest achievement",
      "keywords": ["leader", "champion", "winner", "best", "top", "excellence", "master", "king", "queen"],
      "use_cases": [
        "Class valedictorian",
        "Competition champion",
        "Leadership excellence",
        "Top performer",
        "Master level achievement"
      ]
    },
    {
      "name": "diamond.png",
      "display_name": "Diamond",
      "category": "achievement",
      "description": "Represents premium quality, rare achievement, exceptional performance, valuable skills, and brilliance",
      "keywords": ["premium", "quality", "rare", "valuable", "exceptional", "brilliant", "precious", "elite"],
      "use_cases": [
        "Premium certification",
        "Exceptional achievement",
        "Elite performance",
        "Rare skill mastery",
        "Diamond tier reached"
      ]
    },
    {
      "name": "dna.png",
      "display_name": "DNA",
      "category": "science",
      "description": "Represents biology, genetics, life sciences, biotechnology, medical research, and biological studies",
      "keywords": ["biology", "genetics", "DNA", "life science", "biotechnology", "medical", "research", "genome"],
      "use_cases": [
        "Biology achievement",
        "Genetics course completion",
        "Biotechnology certification",
        "Medical studies excellence",
        "Life science research"
      ]
    },
    {
      "name": "energy.png",
      "display_name": "Energy",
      "category": "science",
      "description": "Represents physics, renewable energy, sustainability, power systems, enthusiasm, and dynamic performance",
      "keywords": ["energy", "power", "physics", "renewable", "sustainability", "electric", "dynamic", "vigor"],
      "use_cases": [
        "Physics achievement",
        "Renewable energy studies",
        "Sustainability project",
        "High energy performance",
        "Environmental science"
      ]
    },
    {
      "name": "gear.png",
      "display_name": "Gear",
      "category": "engineering",
      "description": "Represents engineering, mechanical skills, technical configuration, systems thinking, and process optimization",
      "keywords": ["engineering", "mechanical", "settings", "technical", "machinery", "process", "system", "configuration"],
      "use_cases": [
        "Engineering excellence",
        "Mechanical skills certification",
        "Technical proficiency",
        "Process improvement",
        "System optimization"
      ]
    },
    {
      "name": "gem.png",
      "display_name": "Gem",
      "category": "achievement",
      "description": "Represents precious achievement, special recognition, unique skills, and valuable contribution",
      "keywords": ["precious", "special", "unique", "valuable", "rare", "jewel", "treasure", "exceptional"],
      "use_cases": [
        "Special recognition",
        "Unique achievement",
        "Valuable contribution",
        "Hidden talent discovery",
        "Exceptional skill"
      ]
    },
    {
      "name": "globe.png",
      "display_name": "Globe",
      "category": "geography",
      "description": "Represents global awareness, geography, international studies, world languages, cultural diversity, and environmental studies",
      "keywords": ["global", "world", "geography", "international", "earth", "culture", "diversity", "environment"],
      "use_cases": [
        "Geography excellence",
        "Global studies completion",
        "Language learning achievement",
        "Cultural awareness",
        "International collaboration"
      ]
    },
    {
      "name": "goal.png",
      "display_name": "Goal",
      "category": "achievement",
      "description": "Represents goal achievement, target completion, objective success, milestone reached, and purposeful accomplishment",
      "keywords": ["goal", "target", "objective", "achievement", "milestone", "purpose", "aim", "success"],
      "use_cases": [
        "Goal achievement",
        "Milestone reached",
        "Target exceeded",
        "Objective completed",
        "Personal best"
      ]
    },
    {
      "name": "graduation-cap.png",
      "display_name": "Graduation Cap",
      "category": "academic",
      "description": "Represents academic achievement, graduation, education completion, scholarly success, and learning accomplishment",
      "keywords": ["graduation", "academic", "education", "degree", "diploma", "university", "college", "scholar"],
      "use_cases": [
        "Course graduation",
        "Degree completion",
        "Academic excellence",
        "Education milestone",
        "Certification achieved"
      ]
    },
    {
      "name": "growth.png",
      "display_name": "Growth",
      "category": "progress",
      "description": "Represents personal development, progress, improvement, skill advancement, and continuous learning",
      "keywords": ["growth", "progress", "improvement", "development", "advance", "evolve", "increase", "expand"],
      "use_cases": [
        "Personal development",
        "Skill improvement",
        "Progress milestone",
        "Growth mindset achievement",
        "Continuous improvement"
      ]
    },
    {
      "name": "handshake.png",
      "display_name": "Handshake",
      "category": "collaboration",
      "description": "Represents collaboration, teamwork, partnership, agreement, cooperation, and professional networking",
      "keywords": ["collaboration", "teamwork", "partnership", "cooperation", "agreement", "networking", "deal", "alliance"],
      "use_cases": [
        "Team collaboration excellence",
        "Partnership achievement",
        "Networking success",
        "Cooperation award",
        "Peer mentoring"
      ]
    },
    {
      "name": "ink-bottle.png",
      "display_name": "Ink Bottle",
      "category": "creative",
      "description": "Represents writing skills, creative writing, literature, poetry, journalism, and traditional arts",
      "keywords": ["writing", "literature", "poetry", "creative", "author", "journalism", "essay", "composition"],
      "use_cases": [
        "Creative writing excellence",
        "Literature achievement",
        "Poetry competition",
        "Essay writing award",
        "Journalism skills"
      ]
    },
    {
      "name": "leadership.png",
      "display_name": "Leadership",
      "category": "skills",
      "description": "Represents leadership qualities, management skills, team guidance, decision making, and organizational abilities",
      "keywords": ["leader", "management", "guide", "direct", "organize", "command", "influence", "inspire"],
      "use_cases": [
        "Leadership program completion",
        "Team leader certification",
        "Management training",
        "Student council achievement",
        "Project leadership"
      ]
    },
    {
      "name": "medal.png",
      "display_name": "Medal",
      "category": "achievement",
      "description": "Represents recognition, award, honor, competitive achievement, and distinguished performance",
      "keywords": ["medal", "award", "honor", "recognition", "prize", "achievement", "competition", "distinction"],
      "use_cases": [
        "Competition medal",
        "Honor roll achievement",
        "Distinguished performance",
        "Academic medal",
        "Sports achievement"
      ]
    },
    {
      "name": "microscope.png",
      "display_name": "Microscope",
      "category": "science",
      "description": "Represents scientific research, laboratory skills, biology, detailed analysis, and investigative learning",
      "keywords": ["science", "research", "laboratory", "biology", "analysis", "investigation", "microscopy", "study"],
      "use_cases": [
        "Lab skills certification",
        "Research project completion",
        "Biology excellence",
        "Scientific investigation",
        "Laboratory safety"
      ]
    },
    {
      "name": "music_note.png",
      "display_name": "Music Note",
      "category": "creative",
      "description": "Represents musical talent, music theory, performance arts, rhythm, composition, and audio production",
      "keywords": ["music", "note", "melody", "rhythm", "composition", "performance", "audio", "song"],
      "use_cases": [
        "Music theory completion",
        "Performance excellence",
        "Composition achievement",
        "Instrument mastery",
        "Choir participation"
      ]
    },
    {
      "name": "presentation.png",
      "display_name": "Presentation",
      "category": "communication",
      "description": "Represents presentation skills, public speaking, communication excellence, teaching ability, and information sharing",
      "keywords": ["presentation", "speaking", "communication", "teaching", "lecture", "seminar", "pitch", "demonstration"],
      "use_cases": [
        "Presentation excellence",
        "Public speaking achievement",
        "Teaching assistant",
        "Seminar completion",
        "Demo day winner"
      ]
    },
    {
      "name": "robot.png",
      "display_name": "Robot",
      "category": "technology",
      "description": "Represents robotics, artificial intelligence, automation, STEM education, and technological innovation",
      "keywords": ["robot", "AI", "automation", "robotics", "technology", "innovation", "machine", "artificial"],
      "use_cases": [
        "Robotics club achievement",
        "AI course completion",
        "Automation project",
        "STEM excellence",
        "Innovation award"
      ]
    },
    {
      "name": "shield.png",
      "display_name": "Shield",
      "category": "security",
      "description": "Represents security, protection, cybersecurity, safety, defense, reliability, and trustworthiness",
      "keywords": ["security", "protection", "safety", "defense", "cybersecurity", "guard", "secure", "trust"],
      "use_cases": [
        "Cybersecurity certification",
        "Safety training completion",
        "Security excellence",
        "Data protection skills",
        "Ethical hacking"
      ]
    },
    {
      "name": "solution.png",
      "display_name": "Solution",
      "category": "problem-solving",
      "description": "Represents problem-solving, solution finding, analytical thinking, innovation, and creative resolution",
      "keywords": ["solution", "solve", "answer", "resolve", "fix", "innovation", "breakthrough", "discovery"],
      "use_cases": [
        "Problem-solving excellence",
        "Innovation challenge winner",
        "Solution architect",
        "Debugging champion",
        "Case study completion"
      ]
    },
    {
      "name": "spaceship.png",
      "display_name": "Spaceship",
      "category": "innovation",
      "description": "Represents space science, aerospace, exploration, innovation, ambitious goals, and futuristic thinking",
      "keywords": ["space", "rocket", "aerospace", "exploration", "innovation", "astronomy", "future", "launch"],
      "use_cases": [
        "Space science achievement",
        "Innovation project",
        "Aerospace studies",
        "Ambitious goal reached",
        "STEM exploration"
      ]
    },
    {
      "name": "speech_bubble.png",
      "display_name": "Speech Bubble",
      "category": "communication",
      "description": "Represents communication skills, dialogue, discussion, feedback, conversation, and social interaction",
      "keywords": ["communication", "dialogue", "discussion", "chat", "conversation", "feedback", "talk", "message"],
      "use_cases": [
        "Communication skills",
        "Debate team achievement",
        "Peer feedback excellence",
        "Discussion forum leader",
        "Language proficiency"
      ]
    },
    {
      "name": "star.png",
      "display_name": "Star",
      "category": "achievement",
      "description": "Represents excellence, outstanding performance, favorite status, quality, and special recognition",
      "keywords": ["star", "excellence", "outstanding", "favorite", "quality", "special", "top", "best"],
      "use_cases": [
        "Star student",
        "Outstanding performance",
        "Excellence award",
        "Top rating achieved",
        "Special recognition"
      ]
    },
    {
      "name": "teamwork.png",
      "display_name": "Teamwork",
      "category": "collaboration",
      "description": "Represents team collaboration, group work, cooperative learning, collective achievement, and synergy",
      "keywords": ["team", "collaboration", "group", "together", "cooperative", "collective", "unity", "synergy"],
      "use_cases": [
        "Team project excellence",
        "Group collaboration",
        "Cooperative learning",
        "Team building participation",
        "Collective achievement"
      ]
    },
    {
      "name": "thumbs-up.png",
      "display_name": "Thumbs Up",
      "category": "feedback",
      "description": "Represents approval, positive feedback, encouragement, good job recognition, and satisfaction",
      "keywords": ["approval", "positive", "good", "like", "agree", "encourage", "satisfied", "yes"],
      "use_cases": [
        "Positive peer review",
        "Good behavior award",
        "Encouragement badge",
        "Satisfaction achievement",
        "Approval earned"
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
    }
  ]


# -------------------------
# CONFIGURATION
# -------------------------
MODEL_CONFIG = {
    "model_name": "phi-4-ob:latest",
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

def preprocess_text(text: str) -> str:
    """
    Enhanced text preprocessing for better similarity matching.
    Uses NLTK if available, otherwise falls back to basic preprocessing.
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation and special characters
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    if NLTK_AVAILABLE:
        try:
            # Tokenize
            tokens = word_tokenize(text)
            
            # Remove stopwords and apply stemming
            processed_tokens = []
            for token in tokens:
                if token not in STOP_WORDS and len(token) > 2:
                    stemmed = STEMMER.stem(token)
                    processed_tokens.append(stemmed)
            
            return ' '.join(processed_tokens)
        except Exception as e:
            logger.warning(f"NLTK processing failed, using basic preprocessing: {e}")
            # Fall back to basic preprocessing
            pass
    
    # Basic preprocessing fallback
    words = text.split()
    filtered_words = [word for word in words if word not in STOP_WORDS and len(word) > 2]
    return ' '.join(filtered_words)

def build_weighted_badge_text(badge_name: str, badge_desc: str, custom_instructions: str) -> str:
    """
    Combine badge text with weighted importance.
    Give more weight to badge_name and custom_instructions as they contain key intent.
    """
    # Preprocess each component
    name_processed = preprocess_text(badge_name)
    desc_processed = preprocess_text(badge_desc)
    custom_processed = preprocess_text(custom_instructions)
    
    # Weight: badge_name (2x), custom_instructions (2x), description (1x)
    weighted_components = []
    
    if name_processed:
        weighted_components.extend([name_processed] * 2)  # 2x weight
    
    if desc_processed:
        weighted_components.append(desc_processed)  # 1x weight
    
    if custom_processed:
        weighted_components.extend([custom_processed] * 2)  # 2x weight
    
    return ' '.join(weighted_components)

def build_icon_text(icon: Dict[str, Any]) -> str:
    """Build comprehensive text representation of an icon for TF-IDF matching."""
    components = []
    
    # Core components
    if icon.get("display_name"):
        components.append(icon["display_name"])
    
    if icon.get("name"):
        # Remove file extension and convert to readable text
        name_clean = icon["name"].replace('.png', '').replace('-', ' ').replace('_', ' ')
        components.append(name_clean)
    
    if icon.get("description"):
        components.append(icon["description"])
    
    if icon.get("category"):
        components.append(icon["category"])
    
    # Keywords (high importance)
    keywords = icon.get("keywords", [])
    if keywords:
        components.extend(keywords)
        # Add keywords again for higher weight
        components.extend(keywords)
    
    # Use cases
    use_cases = icon.get("use_cases", [])
    if use_cases:
        components.extend(use_cases)
    
    # Join and preprocess
    full_text = ' '.join([str(comp) for comp in components if comp])
    return preprocess_text(full_text)

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
        prompt += (
            "\n\nISSUING INSTITUTION:\n"
            f"{request.institution}\n"
            "Make sure the institution is clearly and prominently mentioned in the output."
        )

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
        badge_json["raw_model_output"] = text

    return badge_json

async def get_icon_suggestions_for_badge(badge_name: str, badge_description: str, custom_instructions: str = "", top_k: int = 3):
    """
    Generate icon suggestions for a badge based on its metadata.
    
    Args:
        badge_name: The name of the badge (generated by model)
        badge_description: The description of the badge (generated by model)
        custom_instructions: Custom instructions provided during badge creation
        top_k: Number of icon suggestions to return
        
    Returns:
        dict: Contains suggested_icon and icon_candidates
    """
    try:
        # Build weighted badge text for icon matching
        badge_text = build_weighted_badge_text(badge_name, badge_description, custom_instructions)
        
        # Get icon suggestions using enhanced TF-IDF system
        candidates = icon_matcher.suggest_icons(badge_text, top_k=top_k)
        
        if not candidates:
            return {
                "suggested_icon": {"name": ""},
                "icon_candidates": []
            }

        # Format response
        top_candidate = candidates[0]["icon"]
        formatted_candidates = [
            {
                "name": c["icon"]["name"],
                "display_name": c["icon"].get("display_name", ""),
                "category": c["icon"].get("category", ""),
                "score": round(c["score"], 4)
            }
            for c in candidates
        ]

        return {
            "suggested_icon": {"name": top_candidate["name"]},
            "icon_candidates": formatted_candidates
        }

    except Exception as e:
        logger.warning(f"Icon suggestion failed: {e}")
        return {
            "suggested_icon": {"name": ""},
            "icon_candidates": []
        }

# -------------------------
# CLASSES
# -------------------------

class IconMatcher:
    def __init__(self, icons_data: List[Dict[str, Any]]):
        self.icons_data = icons_data
        self.icon_texts = []
        self.vectorizer = None
        self.icon_tfidf_matrix = None
        self._build_tfidf_system()
    
    def _build_tfidf_system(self):
        """Build TF-IDF vectorizer and precompute icon matrix."""
        if not self.icons_data:
            logger.warning("No icons data provided for TF-IDF system")
            return
        
        # Build text representations for all icons
        self.icon_texts = [build_icon_text(icon) for icon in self.icons_data]
        
        # Filter out empty texts
        non_empty_texts = [text for text in self.icon_texts if text.strip()]
        
        if not non_empty_texts:
            logger.warning("No valid icon texts after preprocessing")
            return
        
        try:
            # Configure TF-IDF vectorizer with optimal parameters
            self.vectorizer = TfidfVectorizer(
                max_features=1000,           # Limit vocabulary size
                ngram_range=(1, 2),          # Include unigrams and bigrams
                min_df=1,                    # Include all terms (small dataset)
                max_df=0.95,                 # Remove very common terms
                norm='l2',                   # L2 normalization for cosine similarity
                lowercase=True,              # Already handled in preprocessing
                stop_words=None,             # Already handled in preprocessing
                token_pattern=r'\b\w+\b'     # Word boundaries
            )
            
            # Fit vectorizer and transform icon texts
            self.icon_tfidf_matrix = self.vectorizer.fit_transform(self.icon_texts)
            
            logger.info(f"TF-IDF system initialized with {len(self.icons_data)} icons, "
                       f"vocabulary size: {len(self.vectorizer.vocabulary_)}")
            
        except Exception as e:
            logger.error(f"Failed to build TF-IDF system: {e}")
            self.vectorizer = None
            self.icon_tfidf_matrix = None
    
    def suggest_icons(self, badge_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Suggest icons based on badge text similarity.
        Returns list of dictionaries with icon data and similarity scores.
        """
        if not badge_text or not self.vectorizer or self.icon_tfidf_matrix is None:
            # Return default icon if no valid system
            if self.icons_data:
                return [{"icon": self.icons_data[0], "score": 0.0}]
            return []
        
        try:
            # Preprocess badge text
            processed_badge_text = preprocess_text(badge_text)
            if not processed_badge_text:
                return [{"icon": self.icons_data[0], "score": 0.0}]
            
            # Transform badge text using fitted vectorizer
            badge_tfidf = self.vectorizer.transform([processed_badge_text])
            
            # Calculate cosine similarity
            similarities = cosine_similarity(badge_tfidf, self.icon_tfidf_matrix).flatten()
            
            # Apply keyword matching boost
            similarities = self._apply_keyword_boost(processed_badge_text, similarities)
            
            # Get top-k indices
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            # Build result list
            results = []
            for idx in top_indices:
                if idx < len(self.icons_data):
                    results.append({
                        "icon": self.icons_data[idx],
                        "score": float(similarities[idx])
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in icon suggestion: {e}")
            # Return default icon on error
            if self.icons_data:
                return [{"icon": self.icons_data[0], "score": 0.0}]
            return []
    
    def _apply_keyword_boost(self, badge_text: str, similarities: np.ndarray) -> np.ndarray:
        """
        Apply keyword matching boost to similarity scores.
        This provides additional scoring for exact keyword matches.
        """
        try:
            badge_words = set(badge_text.lower().split())
            
            for i, icon in enumerate(self.icons_data):
                if i >= len(similarities):
                    break
                
                # Get icon keywords
                icon_keywords = icon.get("keywords", [])
                icon_words = set()
                
                for keyword in icon_keywords:
                    icon_words.update(preprocess_text(keyword).split())
                
                # Calculate keyword overlap
                keyword_overlap = len(badge_words.intersection(icon_words))
                
                if keyword_overlap > 0:
                    # Boost score based on keyword matches
                    boost = min(0.3, keyword_overlap * 0.1)  # Max boost of 0.3
                    similarities[i] = min(1.0, similarities[i] + boost)
            
            return similarities
            
        except Exception as e:
            logger.warning(f"Keyword boost failed: {e}")
            return similarities

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
    raw_model_output: str = Field("", alias="raw_model_output")

# Initialize global icon matcher
icon_matcher = IconMatcher(ICONS_DATA)

# -------------------------
# API ENDPOINTS
# -------------------------

@app.post("/generate_badge")
async def generate_badge(request: BadgeRequest):
    """
    Generate badge metadata with icon suggestions in a single API call.
    Returns complete badge data with icon recommendations.
    """
    start_time = time.time()
    try:
        # Step 1: Generate badge JSON from model
        badge_json = await generate_badge_metadata_async(request)

        # Step 2: Validate using pydantic (expecting only 'criteria' field)
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

        # Step 3: Get icon suggestions using the generated badge metadata
        icon_data = await get_icon_suggestions_for_badge(
            badge_name=validated.badge_name,          # ← Generated by model
            badge_description=validated.badge_description,  # ← Generated by model
            custom_instructions=request.custom_instructions, # ← Original user input
            top_k=3
        )

        generation_time = time.time() - start_time
        
        # Step 4: Build complete response
        result = {
            "badge_name": validated.badge_name,
            "badge_description": validated.badge_description,
            "criteria": validated.criteria,
            "suggested_icon": icon_data["suggested_icon"],
            # "icon_candidates": icon_data["icon_candidates"],
            # "generation_time": generation_time,
            # "model_used": MODEL_CONFIG["model_name"],
            # "badge_id": len(badge_history) + 1
        }

        # Step 5: Store in history
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

@app.get("/icons")
async def get_icons():
    """Get all available icons."""
    return {"icons": ICONS_DATA, "total": len(ICONS_DATA)}

@app.get("/system_info")
async def get_system_info():
    """Get system information for debugging."""
    return {
        "nltk_available": NLTK_AVAILABLE,
        "total_icons": len(ICONS_DATA),
        "vectorizer_vocabulary_size": len(icon_matcher.vectorizer.vocabulary_) if icon_matcher.vectorizer else 0,
        "tfidf_matrix_shape": icon_matcher.icon_tfidf_matrix.shape if icon_matcher.icon_tfidf_matrix is not None else "Not initialized"
    }

# -------------------------
# Run with: uvicorn main:app --host 0.0.0.0 --port 8000
# -------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
