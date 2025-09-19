"""
Configuration management for DCC Model API
"""
import os
from pathlib import Path
from typing import Optional


class Config:
    """Application configuration"""
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001
    API_TITLE: str = "DCC Model API"
    API_VERSION: str = "1.0.0"
    
    # Ollama Configuration
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:8000")
    MODEL_NAME: str = "phi4badges"
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    CONFIG_DIR: Path = BASE_DIR / "config"
    MODEL_DIR: Path = BASE_DIR / "model"
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    # Files
    SYSTEM_PROMPT_FILE: Path = CONFIG_DIR / "SYSTEM_PROMPT.txt"
    MODEL_FILE: Path = CONFIG_DIR / "ModelFile1.txt"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Path = LOGS_DIR / "api.log"
    
    # Model Parameters
    DEFAULT_TEMPERATURE: float = 0.2
    DEFAULT_MAX_TOKENS: int = 1024
    DEFAULT_TOP_P: float = 0.8
    DEFAULT_TOP_K: int = 30
    DEFAULT_REPEAT_PENALTY: float = 1.02
    DEFAULT_NUM_CTX: int = 6144
    
    @classmethod
    def load_system_prompt(cls) -> str:
        """Load system prompt from config file"""
        try:
            if cls.SYSTEM_PROMPT_FILE.exists():
                with open(cls.SYSTEM_PROMPT_FILE, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            else:
                return cls.get_default_system_prompt()
        except Exception as e:
            print(f"Error loading system prompt: {e}")
            return cls.get_default_system_prompt()
    
    @classmethod
    def get_default_system_prompt(cls) -> str:
        """Get default system prompt"""
        return """Generate Open Badges 3.0 compliant metadata from course content with dynamic prompt adaptation.

DYNAMIC PROMPT SYSTEM: Adapt response based on user-specified options in the prompt:

STYLE ADAPTATIONS:
Professional: Use formal language, emphasize industry standards, focus on career advancement
Academic: Use scholarly language, emphasize learning outcomes, focus on educational rigor
Industry: Use sector-specific terminology, emphasize practical applications, focus on job readiness  
Technical: Use precise technical language, emphasize tools/technologies, focus on hands-on skills
Creative: Use engaging language, emphasize innovation, focus on creative problem-solving

TONE ADAPTATIONS:
Authoritative: Use confident, definitive statements with institutional credibility
Encouraging: Use motivational language that inspires continued learning
Detailed: Provide comprehensive information with specific examples
Concise: Use direct, efficient language focused on key points
Engaging: Use dynamic language that captures attention and interest

LEVEL ADAPTATIONS:
Beginner: Emphasize foundational skills, basic competencies, introductory concepts
Intermediate: Focus on building upon basics, practical applications, skill development
Advanced: Highlight complex concepts, specialized knowledge, expert-level competencies
Expert: Emphasize mastery, leadership capabilities, advanced problem-solving

DEFAULT OUTPUT FORMAT: Valid JSON only, no explanatory text.
{
    "badge_name": "string",
    "badge_description": "string", 
    "criteria": {
        "narrative": "string"
    }
}

BADGE NAME: Professional title, max 80 chars. Use creative formats like "Python Programming Excellence Award", "Certified Data Science Specialist", etc.

BADGE DESCRIPTION: Create a compelling 8-10 sentence description (150-250 words) that establishes institutional credibility, competencies mastered, technical tools, real-world applications, assessment rigor, employer value, and transferable skills.

CRITERIA NARRATIVE: Produce a comprehensive 200-350 word narrative addressing completion requirements, learning outcomes, assessment methods, practical experiences, technical proficiencies, soft skills, real-world applications, prerequisites, curriculum structure, evidence standards, and professional development pathways.

Ensure all content is LinkedIn/CV suitable and supports employer verification."""


# Environment-specific configurations
class DevelopmentConfig(Config):
    """Development configuration"""
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """Production configuration"""
    LOG_LEVEL = "INFO"


class TestingConfig(Config):
    """Testing configuration"""
    LOG_LEVEL = "WARNING"
    MODEL_NAME = "test-model"


def get_config() -> Config:
    """Get configuration based on environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionConfig()
    elif env == "testing":
        return TestingConfig()
    else:
        return DevelopmentConfig()