import logging
import ssl
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import faiss
import pickle
import os
import tempfile
from pathlib import Path
from sentence_transformers import SentenceTransformer
from laiser.skill_extractor import Skill_Extractor

# Fix SSL certificate verification issues on macOS
# NOTE: This disables SSL verification - use only for trusted sources like GitHub
ssl._create_default_https_context = ssl._create_unverified_context

logger = logging.getLogger(__name__)


class ESCOSkillIndex:
    """ESCO Skills indexing using SentenceTransformer and FAISS with local caching"""

    DEFAULT_ESCO_URL = "https://raw.githubusercontent.com/LAiSER-Software/datasets/refs/heads/master/taxonomies/ESCO_skills_Taxonomy.csv"
    DEFAULT_MODEL = 'sentence-transformers/all-mpnet-base-v2'
    CACHE_DIR = Path("esco_cache")

    def __init__(self):
        self.skill_names: List[str] = []
        self.esco_df: Optional[pd.DataFrame] = None
        self.embeddings: Optional[np.ndarray] = None
        self.index: Optional[faiss.Index] = None
        self.model: Optional[SentenceTransformer] = None
        self._initialized: bool = False

        # Ensure cache directory exists
        self.CACHE_DIR.mkdir(exist_ok=True)

    def initialize(self, esco_url: Optional[str] = None, embedding_model: Optional[str] = None):
        """
        Load ESCO skills, embed them, and create FAISS index

        Args:
            esco_url: URL to ESCO skills CSV (defaults to LAiSER dataset)
            embedding_model: SentenceTransformer model name
        """
        try:
            esco_url = esco_url or self.DEFAULT_ESCO_URL
            embedding_model = embedding_model or self.DEFAULT_MODEL

            logger.info(f"Loading ESCO skills from {esco_url}...")
            self.esco_df = pd.read_csv(esco_url)
            self.skill_names = self.esco_df["preferredLabel"].tolist()
            logger.info(f"Loaded {len(self.skill_names)} ESCO skills")

            # Load embedding model
            logger.info(f"Loading embedding model: {embedding_model}...")
            self.model = SentenceTransformer(embedding_model)

            # Embed ESCO skills
            logger.info("Embedding ESCO skills...")
            self.embeddings = self.model.encode(
                self.skill_names,
                convert_to_numpy=True,
                show_progress_bar=True
            )

            # Create FAISS index with cosine similarity (L2 normalized + Inner Product)
            dimension = self.embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)

            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(self.embeddings)
            # Ensure embeddings are 2D before adding to FAISS index
            if self.embeddings.ndim == 1:
                self.embeddings = np.expand_dims(self.embeddings, axis=0)
            self.index.add(self.embeddings)

            self._initialized = True
            logger.info(f"ESCO skill index initialized successfully! ({len(self.skill_names)} skills indexed)")

        except Exception as e:
            logger.error(f"Failed to initialize ESCO skill index: {e}", exc_info=True)
            self._initialized = False
            raise

    def search_similar_skills(self, query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Find most similar ESCO skills for given text

        Args:
            query_text: Input text to find skills for
            top_k: Number of top skills to return

        Returns:
            List of dicts with skill info and similarity scores
        """
        if not self._initialized or self.model is None:
            logger.warning("ESCO index not initialized")
            return []

        try:
            # Embed query text
            query_embedding = self.model.encode([query_text], convert_to_numpy=True)
            faiss.normalize_L2(query_embedding)

            # Search FAISS index
            distances, indices = self.index.search(query_embedding, top_k)

            # Format results
            results = []
            for i, (idx, score) in enumerate(zip(indices[0], distances[0])):
                skill_info = {
                    "skill": self.skill_names[idx],
                    "score": float(score),
                    "rank": i + 1
                }

                # Add additional metadata from ESCO dataframe if available
                if self.esco_df is not None and idx < len(self.esco_df):
                    row = self.esco_df.iloc[idx]
                    skill_info.update({
                        "uri": row.get("conceptUri", ""),
                        "type": row.get("conceptType", ""),
                        "description": row.get("description", "")
                    })

                results.append(skill_info)

            return results

        except Exception as e:
            logger.error(f"Skill search failed: {e}", exc_info=True)
            return []

    def is_ready(self) -> bool:
        """Check if the index is initialized and ready"""
        return self._initialized


class SkillExtractionService:
    """Service for extracting skills using LAiSER and ESCO FAISS index"""

    def __init__(self):
        self.extractor: Optional[Skill_Extractor] = None
        self.esco_index: Optional[ESCOSkillIndex] = None
        self._initialized: bool = False
        self._esco_initialized: bool = False

    async def initialize(self, ai_model_id: str, hf_token: str = "", use_gpu: bool = False):
        """
        Initialize the skill extractor at startup

        Args:
            ai_model_id: HuggingFace model ID for skill extraction
            hf_token: HuggingFace API token (default: empty string)
            use_gpu: Whether to use GPU acceleration (default: False)
        """
        try:
            logger.info("Initializing LAiSER Skill Extractor with SLM...")
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

    def initialize_esco_index(self, esco_url: Optional[str] = None, embedding_model: Optional[str] = None):
        """
        Initialize ESCO skill index with FAISS

        Args:
            esco_url: Optional custom URL to ESCO skills CSV
            embedding_model: Optional custom SentenceTransformer model
        """
        try:
            logger.info("Initializing ESCO skill index...")
            self.esco_index = ESCOSkillIndex()
            self.esco_index.initialize(esco_url=esco_url, embedding_model=embedding_model)
            self._esco_initialized = True
            logger.info("ESCO skill index ready!")

        except Exception as e:
            logger.error(f"Failed to initialize ESCO index: {e}")
            self._esco_initialized = False
            raise

    def extract_skills(self, text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Extract skills from text using LAiSER with SLM

        Converts text to CSV, processes with LAiSER, and returns skills with:
        - Raw Skill
        - Knowledge Required
        - Task Abilities
        - Skill Tag
        - Correlation Coefficient

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
            logger.info(f"Extracting top {top_k} skills from text using LAiSER with SLM (length: {len(text)} chars)")

            # Step 1: Convert input text to CSV with column 'course_input'
            input_df = pd.DataFrame({'course_input': [text]})

            # Create temporary CSV file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as tmp_file:
                csv_path = tmp_file.name
                input_df.to_csv(csv_path, index=False)
                logger.info(f"Created temporary CSV at: {csv_path}")

            try:
                # Step 2: Extract skills using LAiSER with the CSV file
                logger.info("Processing CSV with LAiSER SLM...")

                # LAiSER's Skill_Extractor processes CSV files with course content
                # The method processes the CSV and returns a DataFrame with extracted skills
                # Try different possible method names based on LAiSER version
                result_df = None

                # Try the most common method names
                if hasattr(self.extractor, 'get_top_skills_from_csv'):
                    result_df = self.extractor.get_top_skills_from_csv(csv_path, top_k=top_k)  # type: ignore
                elif hasattr(self.extractor, 'extract_skills_from_file'):
                    result_df = self.extractor.extract_skills_from_file(csv_path, top_k=top_k)  # type: ignore
                elif hasattr(self.extractor, 'get_skills'):
                    result_df = self.extractor.get_skills(csv_path, top_k=top_k)  # type: ignore
                elif hasattr(self.extractor, 'get_top_esco_skills'):
                    # Fallback: try reading the CSV and passing the text
                    course_text = input_df['course_input'].iloc[0]
                    result_df = self.extractor.get_top_esco_skills(course_text, top_k=top_k)  # type: ignore
                else:
                    logger.error("No compatible extraction method found on Skill_Extractor")
                    logger.info(f"Available methods: {[m for m in dir(self.extractor) if not m.startswith('_')]}")
                    return []

                # Step 3: Parse output and format results
                skills = []

                if result_df is not None:
                    # Handle DataFrame output (CSV processing methods)
                    if isinstance(result_df, pd.DataFrame) and not result_df.empty:
                        # Expected columns from LAiSER output:
                        # - Raw Skill
                        # - Knowledge Required
                        # - Task Abilities
                        # - Skill Tag
                        # - Correlation Coefficient

                        for count, (_, row) in enumerate(result_df.iterrows()):
                            if count >= top_k:
                                break

                            skill_dict = {
                                "skill": str(row.get("Raw Skill", row.get("preferredLabel", ""))),
                                "knowledge_required": str(row.get("Knowledge Required", "")),
                                "task_abilities": str(row.get("Task Abilities", "")),
                                "skill_tag": str(row.get("Skill Tag", "")),
                                "correlation_coefficient": float(row.get("Correlation Coefficient", 0.0)),
                                "extraction_method": "laiser"
                            }
                            skills.append(skill_dict)

                        logger.info(f"Successfully extracted {len(skills)} skills using LAiSER SLM")

                    # Handle list output (text-based fallback method)
                    elif isinstance(result_df, list) and len(result_df) > 0:
                        for skill_item in result_df[:top_k]:
                            if isinstance(skill_item, dict):
                                # Add extraction_method tag to existing dict
                                skill_item["extraction_method"] = "laiser"
                                skills.append(skill_item)
                            else:
                                # Convert to standard format
                                skills.append({
                                    "skill": str(skill_item),
                                    "extraction_method": "laiser"
                                })

                        logger.info(f"Successfully extracted {len(skills)} skills using LAiSER SLM (fallback mode)")
                    else:
                        logger.warning("LAiSER returned empty or None result")
                else:
                    logger.warning("LAiSER returned None")

                return skills

            finally:
                # Clean up temporary CSV file
                if os.path.exists(csv_path):
                    os.unlink(csv_path)
                    logger.debug(f"Cleaned up temporary CSV: {csv_path}")

        except Exception as e:
            logger.error(f"Skill extraction failed: {e}", exc_info=True)
            return []

    def extract_skills_with_esco(self, text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Extract skills from text using ESCO FAISS index

        Args:
            text: Input text (course content or badge description)
            top_k: Number of top skills to extract

        Returns:
            List of extracted skills with similarity scores and metadata
        """
        if not self._esco_initialized or not self.esco_index:
            logger.warning("ESCO index not initialized, returning empty list")
            return []

        try:
            logger.info(f"Extracting top {top_k} ESCO skills from text (length: {len(text)} chars)")

            # Extract skills using ESCO FAISS index
            skills = self.esco_index.search_similar_skills(text, top_k=top_k)

            logger.info(f"Successfully extracted {len(skills)} ESCO skills")
            return skills

        except Exception as e:
            logger.error(f"ESCO skill extraction failed: {e}", exc_info=True)
            return []

    def is_ready(self) -> bool:
        """Check if the extractor is initialized and ready"""
        return self._initialized and self.extractor is not None

    def is_esco_ready(self) -> bool:
        """Check if the ESCO index is initialized and ready"""
        return self._esco_initialized and self.esco_index is not None

# Global singleton instance
skill_service = SkillExtractionService()
