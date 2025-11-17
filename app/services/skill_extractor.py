import logging
import ssl
from typing import List, Dict, Any, Optional
from laiser.skill_extractor import Skill_Extractor

# Fix SSL certificate verification issues on macOS
# NOTE: This disables SSL verification - use only for trusted sources like GitHub
ssl._create_default_https_context = ssl._create_unverified_context

logger = logging.getLogger(__name__)

class SkillExtractionService:
    """Service for extracting skills using LAiSER"""

    def __init__(self):
        self.extractor: Optional[Skill_Extractor] = None
        self._initialized: bool = False

    async def initialize(self, ai_model_id: str, hf_token: str, use_gpu: bool = True):
        """
        Initialize the skill extractor at startup

        Args:
            ai_model_id: HuggingFace model ID for skill extraction
            hf_token: HuggingFace API token
            use_gpu: Whether to use GPU acceleration
        """
        try:
            logger.info("Initializing LAiSER Skill Extractor...")
            logger.info(f"Model: {ai_model_id}, GPU: {use_gpu}")

            self.extractor = Skill_Extractor(
                AI_MODEL_ID=ai_model_id,
                HF_TOKEN=hf_token,
                use_gpu=use_gpu
            )

            self._initialized = True
            logger.info("LAiSER Skill Extractor initialized successfully!")

        except Exception as e:
            logger.error(f"Failed to initialize LAiSER: {e}")
            self._initialized = False
            raise

    def extract_skills(self, text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Extract skills from text

        Args:
            text: Input text (course content or badge description)
            top_k: Number of top skills to extract

        Returns:
            List of extracted skills with metadata
        """
        if not self._initialized or not self.extractor:
            logger.warning("Skill extractor not initialized, returning empty list")
            return []

        try:
            logger.info(f"Extracting top {top_k} skills from text (length: {len(text)} chars)")

            # Extract skills using LAiSER
            skills = self.extractor.get_top_esco_skills(text, top_k=top_k)

            logger.info(f"Successfully extracted {len(skills)} skills")
            return skills

        except Exception as e:
            logger.error(f"Skill extraction failed: {e}", exc_info=True)
            return []

    def is_ready(self) -> bool:
        """Check if the extractor is initialized and ready"""
        return self._initialized and self.extractor is not None

# Global singleton instance
skill_service = SkillExtractionService()
