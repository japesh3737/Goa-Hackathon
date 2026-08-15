import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class RAGCache:
    def __init__(self, cache_file: str = "data/processed/rag_cache.json"):
        self.cache_file = cache_file
        self.cache: Dict[str, Any] = {}
        self.load_cache()

    def load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} entries from RAG cache.")
        except Exception as e:
            logger.warning(f"Failed to load RAG cache from file: {e}")
            self.cache = {}

    def save_cache(self):
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
            logger.info("Saved RAG cache to file.")
        except Exception as e:
            logger.warning(f"Failed to save RAG cache to file: {e}")

    def get(self, query: str) -> Optional[Dict[str, Any]]:
        cleaned_query = query.strip().lower()
        cleaned_query = cleaned_query.rstrip("?.!")
        return self.cache.get(cleaned_query)

    def set(self, query: str, response: Dict[str, Any]):
        cleaned_query = query.strip().lower()
        cleaned_query = cleaned_query.rstrip("?.!")
        self.cache[cleaned_query] = response
        self.save_cache()

    def clear(self):
        self.cache = {}
        if os.path.exists(self.cache_file):
            try:
                os.remove(self.cache_file)
            except Exception:
                pass
        logger.info("RAG cache cleared.")

rag_cache = RAGCache()
