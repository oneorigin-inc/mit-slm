import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING

# Heavy LAiSER dependencies (pandas, laiser, ...) are imported lazily inside the
# methods that need them. This service is currently disabled (skill extraction is
# handled by the frontend), so importing this module must stay cheap and must not
# fail when those optional dependencies are absent.
if TYPE_CHECKING:  # pragma: no cover - typing only, not imported at runtime
    from laiser.skill_extractor import Skill_Extractor

logger = logging.getLogger(__name__)

def to_title_case(text: str) -> str:
    """Convert text to Title Case (e.g., 'machine learning' -> 'Machine Learning')"""
    return text.title() if text else text

class SkillExtractionService:
    """
    Service for extracting skills using LAiSER
    
    Production service with required LAiSER dependencies.
    Expects all dependencies (pandas, laiser, scikit-learn, scipy, transformers) to be installed.
    """

    def __init__(self):
        self.extractor: Optional["Skill_Extractor"] = None
        self._initialized: bool = False

    async def initialize(self, ai_model_id: str, hf_token: str, use_gpu: bool = False):
        """
        Initialize the LAiSER skill extractor at application startup
        
        Args:
            ai_model_id: HuggingFace model ID for skill extraction (e.g., 'bert-base-uncased')
            hf_token: HuggingFace API token (can be empty string for public models)
            use_gpu: Whether to use GPU acceleration (False for CPU mode)
            
        Raises:
            Exception: If LAiSER initialization fails
        """
        logger.info("=" * 80)
        logger.info("Initializing LAiSER Skill Extractor (Production Mode)")
        logger.info(f"Model: {ai_model_id}")
        logger.info(f"GPU: {use_gpu}")
        logger.info(f"ESCO Taxonomy: Full (10,000+ skills)")
        logger.info("=" * 80)

        try:
            # Imported lazily so the module stays importable without LAiSER installed.
            from laiser.skill_extractor import Skill_Extractor

            self.extractor = Skill_Extractor(
                AI_MODEL_ID=ai_model_id,
                HF_TOKEN=hf_token,
                use_gpu=use_gpu
            )

            self._initialized = True
            logger.info("✅ LAiSER Skill Extractor initialized successfully!")
            logger.info("=" * 80)

        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ Failed to initialize LAiSER: {e}")
            logger.error("=" * 80)
            self._initialized = False
            raise

    def extract_skills(self, text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Extract skills from text using LAiSER's ESCO-aligned extraction pipeline
        
        Args:
            text: Input text (course content or badge description)
            top_k: Number of top skills to extract (default: 10)
            
        Returns:
            List of skill dictionaries with Open Badge v3 alignment format:
            - targetName: Skill name in Title Case
            - targetDescription: ESCO skill description
            - targetUrl: ESCO concept URI
            - Skill Tag: ESCO code (e.g., "ESCO.1234")
            - Correlation Coefficient: Similarity score (0-1)
            - type: "Alignment"
            - targetType: "ESCO:Skill"
            
        Note: 
            - With use_gpu=False: Uses SkillNer (fast CPU-based pattern matching)
            - With use_gpu=True: Adds LLM enrichment (Knowledge Required, Task Abilities)
        """
        if not self._initialized or not self.extractor:
            logger.error("❌ Skill extractor not initialized - cannot extract skills")
            return []

        try:
            import time
            # Imported lazily so the module stays importable without pandas installed.
            import pandas as pd
            start_time = time.time()

            logger.info(f"🔍 Extracting top {top_k} skills from text (length: {len(text)} chars)")

            # Create DataFrame for LAiSER extractor
            data = pd.DataFrame({
                'id': ['badge_1'],
                'description': [text]
            })

            # Use LAiSER's full extractor function
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

            # Enrich skills with ESCO metadata and transform to Open Badge v3 format
            enriched_skills = []
            for skill in skills:
                # Remove internal field
                skill.pop('Research ID', None)

                raw_skill = skill.get('Raw Skill', '')
                
                # Transform to Open Badge v3 alignment format
                if raw_skill:
                    skill['targetName'] = to_title_case(raw_skill)
                else:
                    skill['targetName'] = ''
                
                # Remove old field name
                skill.pop('Raw Skill', None)

                # Enrich with ESCO taxonomy data
                if raw_skill and self.extractor.esco_df is not None:
                    esco_match = self.extractor.esco_df[
                        self.extractor.esco_df['preferredLabel'] == raw_skill
                    ]
                    if not esco_match.empty:
                        esco_row = esco_match.iloc[0]
                        skill['targetDescription'] = esco_row.get('description', '')
                        skill['targetUrl'] = esco_row.get('conceptUri', '')
                    else:
                        skill['targetDescription'] = ''
                        skill['targetUrl'] = ''
                else:
                    skill['targetDescription'] = ''
                    skill['targetUrl'] = ''

                # Remove legacy fields
                skill.pop('Description', None)
                skill.pop('URI', None)

                # Add Open Badge v3 alignment fields
                skill['type'] = 'Alignment'
                skill['targetType'] = 'ESCO:Skill'

                enriched_skills.append(skill)

            extraction_time = time.time() - start_time
            logger.info(f"✅ Successfully extracted {len(enriched_skills)} skills with ESCO metadata in {extraction_time:.2f}s")
            
            # Log top 3 skills for debugging
            if enriched_skills:
                logger.debug("Top 3 skills:")
                for i, skill in enumerate(enriched_skills[:3], 1):
                    logger.debug(f"  {i}. {skill['targetName']} (score: {skill.get('Correlation Coefficient', 0):.3f})")
            
            from typing import cast
            return cast(List[Dict[str, Any]], enriched_skills)

        except Exception as e:
            logger.error(f"❌ Skill extraction failed: {e}", exc_info=True)
            return []

    def is_ready(self) -> bool:
        """
        Check if the LAiSER extractor is initialized and ready for use
        
        Returns:
            bool: True if extractor is initialized, False otherwise
        """
        return self._initialized and self.extractor is not None

# Global singleton instance
skill_service = SkillExtractionService()
