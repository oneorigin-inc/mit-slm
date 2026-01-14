import logging
import ssl
from typing import List, Dict, Any, Optional

# LAiSER DISABLED BY DEFAULT - Uncomment imports and code below to enable
# LAiSER imports - try new refactored API first, fall back to legacy
# try:
#     from laiser.skill_extractor_refactored import SkillExtractorRefactored
#     LAISER_NEW_API_AVAILABLE = True
# except ImportError:
#     LAISER_NEW_API_AVAILABLE = False
#     SkillExtractorRefactored = None  # type: ignore
#
# try:
#     from laiser.skill_extractor import Skill_Extractor
#     LAISER_LEGACY_API_AVAILABLE = True
# except ImportError:
#     LAISER_LEGACY_API_AVAILABLE = False
#     Skill_Extractor = None  # type: ignore
#
# # Required for LAiSER data processing
# try:
#     import pandas as pd
#     PANDAS_AVAILABLE = True
# except ImportError:
#     PANDAS_AVAILABLE = False
#     pd = None  # type: ignore

# Fix SSL certificate verification issues on macOS
# NOTE: This disables SSL verification - use only for trusted sources like GitHub
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass  # Ignore SSL setup errors

logger = logging.getLogger(__name__)

def to_title_case(text: str) -> str:
    """Convert text to Title Case (e.g., 'machine learning' -> 'Machine Learning')"""
    return text.title() if text else text

class SkillExtractionService:
    """
    Service for extracting skills using LAiSER
    
    LAiSER DISABLED BY DEFAULT - Returns empty results
    Uncomment code below to enable LAiSER integration.
    
    Supports both new refactored API (recommended) and legacy API.
    Uses CPU-only mode (use_gpu=False) and handles missing model credentials.
    
    Based on: https://github.com/LAiSER-Software/extract-module
    """

    def __init__(self):
        # LAiSER DISABLED BY DEFAULT
        self.extractor = None
        self._initialized: bool = False
        self._api_type: Optional[str] = None  # 'new' or 'legacy'

    async def initialize(self, ai_model_id: str = "", hf_token: str = "", use_gpu: bool = False):
        """
        Initialize the LAiSER skill extractor at application startup
        
        LAiSER DISABLED BY DEFAULT - This method does nothing now
        
        Args:
            ai_model_id: HuggingFace model ID for skill extraction (optional, empty string uses defaults)
            hf_token: HuggingFace API token (optional, empty string for public models)
            use_gpu: Whether to use GPU acceleration (False for CPU mode)
            
        Raises:
            Exception: If LAiSER initialization fails
        """
        logger.info("=" * 80)
        logger.info("LAiSER Skill Extractor - DISABLED BY DEFAULT")
        logger.info("Skill extraction will return empty results")
        logger.info("Uncomment code in skill_extractor.py to enable LAiSER")
        logger.info("=" * 80)
        self._initialized = False
        
        # LAiSER DISABLED BY DEFAULT - Uncomment below to enable
        # logger.info("=" * 80)
        # logger.info("Initializing LAiSER Skill Extractor")
        # logger.info(f"API: {'New (Refactored)' if LAISER_NEW_API_AVAILABLE else 'Legacy' if LAISER_LEGACY_API_AVAILABLE else 'None Available'}")
        # logger.info(f"Model ID: {ai_model_id if ai_model_id else 'Default (not specified)'}")
        # logger.info(f"HF Token: {'Provided' if hf_token else 'Not provided (using public models)'}")
        # logger.info(f"GPU: {use_gpu} (CPU-only mode: {not use_gpu})")
        # logger.info(f"ESCO Taxonomy: Full (10,000+ skills)")
        # logger.info("=" * 80)
        #
        # if not PANDAS_AVAILABLE:
        #     error_msg = "Pandas is required for LAiSER but not installed"
        #     logger.error(f"❌ {error_msg}")
        #     raise ImportError(error_msg)
        #
        # try:
        #     # Try new refactored API first (recommended)
        #     if LAISER_NEW_API_AVAILABLE:
        #         logger.info("Attempting to use new refactored API (SkillExtractorRefactored)...")
        #         try:
        #             # New API uses different parameter names
        #             if ai_model_id:
        #                 self.extractor = SkillExtractorRefactored(
        #                     model_id=ai_model_id,
        #                     hf_token=hf_token if hf_token else None,
        #                     use_gpu=use_gpu
        #                 )
        #             else:
        #                 # Try without model_id (may use defaults)
        #                 logger.info("No model_id provided, attempting initialization with defaults...")
        #                 self.extractor = SkillExtractorRefactored(
        #                     model_id=None,  # or try empty string
        #                     hf_token=hf_token if hf_token else None,
        #                     use_gpu=use_gpu
        #                 )
        #             self._api_type = 'new'
        #             self._initialized = True
        #             logger.info("✅ LAiSER Skill Extractor (New API) initialized successfully!")
        #             logger.info("=" * 80)
        #             return
        #         except Exception as e:
        #             logger.warning(f"⚠️ New API initialization failed: {e}")
        #             logger.info("Falling back to legacy API...")
        #             # Fall through to legacy API
        #
        #     # Fall back to legacy API
        #     if LAISER_LEGACY_API_AVAILABLE:
        #         logger.info("Using legacy API (Skill_Extractor)...")
        #         # Legacy API uses uppercase parameter names
        #         if ai_model_id:
        #             self.extractor = Skill_Extractor(
        #                 AI_MODEL_ID=ai_model_id,
        #                 HF_TOKEN=hf_token,
        #                 use_gpu=use_gpu
        #             )
        #         else:
        #             # Try with default model if not provided
        #             logger.info("No model_id provided, using default 'bert-base-uncased'...")
        #             self.extractor = Skill_Extractor(
        #                 AI_MODEL_ID="bert-base-uncased",  # Default model
        #                 HF_TOKEN=hf_token,
        #                 use_gpu=use_gpu
        #             )
        #         self._api_type = 'legacy'
        #         self._initialized = True
        #         logger.info("✅ LAiSER Skill Extractor (Legacy API) initialized successfully!")
        #         logger.info("=" * 80)
        #         return
        #     else:
        #         raise ImportError("Neither new nor legacy LAiSER API is available")
        #
        # except Exception as e:
        #     logger.error("=" * 80)
        #     logger.error(f"❌ Failed to initialize LAiSER: {e}")
        #     logger.error("=" * 80)
        #     self._initialized = False
        #     raise

    def extract_skills(self, text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Extract skills from text using LAiSER's ESCO-aligned extraction pipeline
        
        LAiSER DISABLED BY DEFAULT - Returns empty list
        
        Args:
            text: Input text (course content or badge description)
            top_k: Number of top skills to extract (default: 10)
            
        Returns:
            Empty list (LAiSER is disabled by default)
        """
        logger.warning("⚠️ LAiSER skill extraction is disabled by default. Returning empty skills list.")
        logger.warning("Uncomment code in skill_extractor.py to enable LAiSER")
        return []
        
        # LAiSER DISABLED BY DEFAULT - Uncomment below to enable
        # if not self._initialized or not self.extractor:
        #     logger.error("❌ Skill extractor not initialized - cannot extract skills")
        #     return []
        #
        # try:
        #     import time
        #     start_time = time.time()
        #     
        #     logger.info(f"🔍 Extracting top {top_k} skills from text (length: {len(text)} chars)")
        #
        #     # Create DataFrame for LAiSER extractor
        #     data = pd.DataFrame({
        #         'id': ['badge_1'],
        #         'description': [text]
        #     })
        #
        #     # Use LAiSER's extractor function (both APIs use similar interface)
        #     if self._api_type == 'new':
        #         # New API might have different method name - adjust as needed
        #         # For now, assume it has similar interface
        #         result_df = self.extractor.extract(
        #             data=data,
        #             id_column='id',
        #             text_columns=['description'],
        #             top_k=top_k
        #         )
        #     else:
        #         # Legacy API
        #         result_df = self.extractor.extractor(
        #             data=data,
        #             id_column='id',
        #             text_columns=['description'],
        #             input_type='job_desc',
        #             top_k=top_k,
        #             levels=False,
        #             warnings=False
        #         )
        #
        #     # Convert to list of dicts
        #     if isinstance(result_df, pd.DataFrame):
        #         skills = list(result_df.to_dict('records'))  # type: ignore
        #     else:
        #         skills = list(result_df) if isinstance(result_df, list) else []
        #
        #     # Enrich skills with ESCO metadata and transform to Open Badge v3 format
        #     enriched_skills = []
        #     for skill in skills:
        #         # Remove internal field
        #         skill.pop('Research ID', None)
        #
        #         raw_skill = skill.get('Raw Skill', '')
        #         
        #         # Transform to Open Badge v3 alignment format
        #         if raw_skill:
        #             skill['targetName'] = to_title_case(raw_skill)
        #         else:
        #             skill['targetName'] = ''
        #         
        #         # Remove old field name
        #         skill.pop('Raw Skill', None)
        #
        #         # Enrich with ESCO taxonomy data (if available)
        #         if raw_skill and hasattr(self.extractor, 'esco_df') and self.extractor.esco_df is not None:
        #             esco_match = self.extractor.esco_df[
        #                 self.extractor.esco_df['preferredLabel'] == raw_skill
        #             ]
        #             if not esco_match.empty:
        #                 esco_row = esco_match.iloc[0]
        #                 skill['targetDescription'] = esco_row.get('description', '')
        #                 skill['targetUrl'] = esco_row.get('conceptUri', '')
        #             else:
        #                 skill['targetDescription'] = ''
        #                 skill['targetUrl'] = ''
        #         else:
        #             skill['targetDescription'] = ''
        #             skill['targetUrl'] = ''
        #
        #         # Remove legacy fields
        #         skill.pop('Description', None)
        #         skill.pop('URI', None)
        #
        #         # Add Open Badge v3 alignment fields
        #         skill['type'] = 'Alignment'
        #         skill['targetType'] = 'ESCO:Skill'
        #
        #         enriched_skills.append(skill)
        #
        #     extraction_time = time.time() - start_time
        #     logger.info(f"✅ Successfully extracted {len(enriched_skills)} skills with ESCO metadata in {extraction_time:.2f}s")
        #     
        #     # Log top 3 skills for debugging
        #     if enriched_skills:
        #         logger.debug("Top 3 skills:")
        #         for i, skill in enumerate(enriched_skills[:3], 1):
        #             logger.debug(f"  {i}. {skill['targetName']} (score: {skill.get('Correlation Coefficient', 0):.3f})")
        #     
        #     from typing import cast
        #     return cast(List[Dict[str, Any]], enriched_skills)
        #
        # except Exception as e:
        #     logger.error(f"❌ Skill extraction failed: {e}", exc_info=True)
        #     return []

    def is_ready(self) -> bool:
        """
        Check if the LAiSER extractor is initialized and ready for use
        
        Returns:
            bool: True if extractor is initialized, False otherwise
        """
        return self._initialized and self.extractor is not None

# Global singleton instance
skill_service = SkillExtractionService()
