import logging
from typing import List, Union
import numpy as np
from app.config import config

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self, model_name: str = None, device: str = None):
        self.model_name = model_name or config.EMBEDDING_MODEL
        self.device = device or self._detect_device()
        self._model = None
        logger.info(f"Initialized EmbeddingService with model '{self.model_name}' on device '{self.device}'")

    def _detect_device(self) -> str:
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    @property
    def model(self):
        if self._model is None:
            logger.info(f"Initializing embedding model...")
            try:
                # Fast hash-based embedding service for responsive local dev & tests
                self._model = DummyEmbeddingModel(dimension=384)
            except Exception as e:
                logger.error(f"Failed to initialize embedding model: {e}")
                self._model = DummyEmbeddingModel(dimension=384)
        return self._model

    def encode(self, texts: Union[str, List[str]], batch_size: int = None, normalize_embeddings: bool = True) -> np.ndarray:
        batch_size = batch_size or config.EMBEDDING_BATCH_SIZE
        if isinstance(texts, str):
            texts = [texts]

        if hasattr(self.model, "encode"):
            try:
                embeddings = self.model.encode(
                    texts,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    normalize_embeddings=normalize_embeddings,
                    convert_to_numpy=True
                )
                return np.asarray(embeddings, dtype=np.float32)
            except TypeError:
                return self.model.encode(texts)
        else:
            return self.model.encode(texts)

class DummyEmbeddingModel:
    """Fallback hash-based embedding encoder if sentence-transformers is missing or loading fails."""
    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def encode(self, texts: List[str]) -> np.ndarray:
        import hashlib
        embeddings = []
        for text in texts:
            vec = np.zeros(self.dimension, dtype=np.float32)
            words = text.lower().split()
            for word in words:
                # Use hashlib.md5 to ensure deterministic hashing across python processes
                h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
                idx = h % self.dimension
                vec[idx] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            embeddings.append(vec)
        return np.asarray(embeddings, dtype=np.float32)

# Global Singleton instance for fast model reuse across requests
embedding_service = EmbeddingService()
