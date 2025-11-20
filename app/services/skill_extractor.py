import logging
import ssl
import pandas as pd
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
        Extract skills from text using LAiSER's full extractor pipeline

        Args:
            text: Input text (course content or badge description)
            top_k: Number of top skills to extract

        Returns:
            List of dicts with skill metadata:
            - Research ID: Badge identifier
            - Raw Skill: Skill name from ESCO taxonomy
            - Skill Tag: ESCO code (e.g., "ESCO.1234")
            - Knowledge Required: List (empty if use_gpu=False)
            - Task Abilities: List (empty if use_gpu=False)
            - Correlation Coefficient: Similarity score (0-1)

        Note: With use_gpu=False (current setting), uses fast SkillNer extraction.
              Knowledge Required and Task Abilities will be empty lists.
        """
        if not self._initialized or not self.extractor:
            logger.warning("Skill extractor not initialized, returning empty list")
            return []

        try:
            logger.info(f"Extracting top {top_k} skills from text (length: {len(text)} chars)")

            # Create DataFrame for LAiSER extractor
            data = pd.DataFrame({
                'id': ['badge_1'],
                'description': [text]
            })

            # Use LAiSER's full extractor function
            # With use_gpu=False: Uses SkillNer (fast pattern matching)
            # With use_gpu=True: Uses LLM for enrichment (Knowledge Required, Task Abilities)
            result_df = self.extractor.extractor(
                data=data,
                id_column='id',
                text_columns=['description'],
                input_type='job_desc',
                top_k=top_k,
                levels=False,
                warnings=False
            )

            # Convert to list of dicts
            if isinstance(result_df, pd.DataFrame):
                skills = list(result_df.to_dict('records'))  # type: ignore
            else:
                skills = list(result_df) if isinstance(result_df, list) else []

            # Enrich skills with ESCO description and URI
            enriched_skills = []
            for skill in skills:
                # Remove Research ID 
                skill.pop('Research ID', None)

                raw_skill = skill.get('Raw Skill', '')
                if raw_skill and self.extractor.esco_df is not None:
                    # Find matching ESCO entry
                    esco_match = self.extractor.esco_df[
                        self.extractor.esco_df['preferredLabel'] == raw_skill
                    ]
                    if not esco_match.empty:
                        esco_row = esco_match.iloc[0]
                        # Replace Description with ESCO description (or empty if not found)
                        skill['Description'] = esco_row.get('description', '')
                        # Add ESCO URI
                        skill['URI'] = esco_row.get('conceptUri', '')
                    else:
                        # No ESCO match - set description to empty
                        skill['Description'] = ''
                        skill['URI'] = ''
                else:
                    # No raw skill or esco_df not available
                    skill['Description'] = ''
                    skill['URI'] = ''

                enriched_skills.append(skill)

            logger.info(f"Successfully extracted {len(enriched_skills)} skills with ESCO metadata")
            from typing import cast
            return cast(List[Dict[str, Any]], enriched_skills)

        except Exception as e:
            logger.error(f"Skill extraction failed: {e}", exc_info=True)
            return []

    def is_ready(self) -> bool:
        """Check if the extractor is initialized and ready"""
        return self._initialized and self.extractor is not None

# Global singleton instance
skill_service = SkillExtractionService()
