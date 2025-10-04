from pydantic_settings import BaseSettings  # Changed from pydantic import BaseSettings
from pydantic import Field
from typing import Dict, List
import os

class Settings(BaseSettings):
    # Ollama Configuration  
    OLLAMA_API_URL: str = "http://localhost:11434/api/generate"
    MODEL_NAME: str = "phi4-chat:latest"
    
    # Model Configuration
    MODEL_CONFIG: Dict = {
        "temperature": 0.15,
        "top_p": 0.8,
        "top_k": 30,
        "num_predict": 1024,
        "repeat_penalty": 1.05,
        "num_ctx": 4096,
        "stop": ["<|end|>", "}\n\n"]
    }
    
    # Asset paths
    ASSETS_PATH: str = "assets/"
    ICONS_PATH: str = "assets/icons/"
    LOGOS_PATH: str = "assets/logos/"
    FONTS_PATH: str = "assets/fonts/"
    
    # NLTK Configuration
    NLTK_AVAILABLE: bool = True
    
    # Style Descriptions
    STYLE_DESCRIPTIONS: Dict = {
        "Professional": "Use formal, business-oriented language emphasizing industry standards and career advancement.",
        "Academic": "Use scholarly language emphasizing learning outcomes and academic rigor.",
        "Industry": "Use sector-specific terminology focusing on job-readiness and practical applications.",
        "Technical": "Use precise technical language with emphasis on tools and measurable outcomes.",
        "Creative": "Use engaging language highlighting innovation and problem-solving."
    }
    
    TONE_DESCRIPTIONS: Dict = {
        "Authoritative": "Confident, definitive tone with institutional credibility.",
        "Encouraging": "Motivating, supportive tone inspiring continued learning.",
        "Detailed": "Comprehensive detail with examples and specific metrics.",
        "Concise": "Short, direct guidance focusing on essential information.",
        "Engaging": "Dynamic, compelling language to capture attention."
    }
    
    LEVEL_DESCRIPTIONS: Dict = {
        "Beginner": "Target learners with minimal prior knowledge; focus on foundations.",
        "Intermediate": "Target learners with basic familiarity; emphasize applied tasks.",
        "Advanced": "Target learners with solid foundations; emphasize complex problem solving."
    }
    
    CRITERION_TEMPLATES: Dict = {
        "Task-Oriented": "[Action verb], [action verb], [action verb]... (imperative commands directing learners to perform tasks)",
        "Evidence-Based": "Learner has/can/successfully [action verb], has/can/effectively [action verb], has/can/accurately [action verb]... (focusing on demonstrated abilities and accomplishments)",
        "Outcome-Focused": "Students will be able to [action verb], will be prepared to [action verb], will [action verb]... (future tense emphasizing expected outcomes and capabilities)"
    }
    
    model_config = {"env_file": ".env"}  # Updated for Pydantic v2

settings = Settings()
