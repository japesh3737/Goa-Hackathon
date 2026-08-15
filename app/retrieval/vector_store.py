import os
import pickle
import logging
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from app.config import config
from app.models.schemas import DocumentChunk
from app.retrieval.embeddings import embedding_service

logger = logging.getLogger(__name__)

class FAISSVectorStore:
    def __init__(self, index_path: str = None, metadata_path: str = None):
        self._index_path = index_path
        self._metadata_path = metadata_path
        self.index = None
        self.documents: List[DocumentChunk] = []
        self.dimension = 384

    @property
    def index_path(self) -> str:
        return self._index_path or str(config.VECTOR_STORE_PATH)

    @property
    def metadata_path(self) -> str:
        return self._metadata_path or str(config.METADATA_STORE_PATH)

    def build_index(self, documents: List[DocumentChunk]):
        """Builds a FAISS index from a list of DocumentChunks with title-contextualized embeddings."""
        if not documents:
            logger.warning("No documents provided to build vector index.")
            return

        self.documents = documents
        # Embed with Title prefix to maximize dense semantic matching precision
        texts = [
            f"{doc.title}: {doc.text}" if doc.title and not doc.text.startswith(doc.title) else doc.text 
            for doc in documents
        ]
        logger.info(f"Generating embeddings for {len(texts)} document chunks...")
        embeddings = embedding_service.encode(texts, normalize_embeddings=True)
        self.dimension = embeddings.shape[1]

        try:
            import faiss
            logger.info(f"Initializing FAISS IndexFlatIP (dim={self.dimension})...")
            index = faiss.IndexFlatIP(self.dimension)
            index.add(embeddings.astype(np.float32))
            self.index = index
        except Exception as e:
            logger.warning(f"FAISS package not available or index build failed: {e}. Using NumPy Flat Vector Store fallback.")
            self.index = NumPyVectorStore(embeddings)

        self.save_index()
        logger.info(f"Vector store successfully built and saved with {len(documents)} items.")

    def save_index(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.metadata_path), exist_ok=True)

        # Save FAISS index
        try:
            import faiss
            if isinstance(self.index, faiss.Index):
                faiss.write_index(self.index, self.index_path)
            else:
                with open(self.index_path, "wb") as f:
                    pickle.dump(self.index, f)
        except Exception as e:
            with open(self.index_path, "wb") as f:
                pickle.dump(self.index, f)

        # Save Metadata
        with open(self.metadata_path, "wb") as f:
            pickle.dump([doc.model_dump() for doc in self.documents], f)
        logger.info(f"Saved vector index to {self.index_path} and metadata to {self.metadata_path}")

    def load_index(self) -> bool:
        if not os.path.exists(self.index_path) or not os.path.exists(self.metadata_path):
            logger.warning("Vector index or metadata files do not exist locally.")
            return False

        try:
            # Load metadata
            with open(self.metadata_path, "rb") as f:
                raw_docs = pickle.load(f)
                self.documents = [DocumentChunk(**doc) if isinstance(doc, dict) else doc for doc in raw_docs]

            # Load FAISS index
            try:
                import faiss
                self.index = faiss.read_index(self.index_path)
            except Exception:
                with open(self.index_path, "rb") as f:
                    self.index = pickle.load(f)

            logger.info(f"Loaded vector store with {len(self.documents)} indexed documents.")
            return True
        except Exception as e:
            logger.error(f"Failed to load vector index: {e}")
            return False

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        if self.index is None or not self.documents:
            if not self.load_index():
                return []

        top_k = min(top_k, len(self.documents))
        if top_k <= 0:
            return []

        if len(query_vector.shape) == 1:
            query_vector = np.expand_dims(query_vector, axis=0)

        # Search index
        if hasattr(self.index, "search"): # FAISS index
            scores, indices = self.index.search(query_vector.astype(np.float32), top_k)
            scores = scores[0]
            indices = indices[0]
        else: # NumPy fallback
            scores, indices = self.index.search(query_vector, top_k)

        results = []
        for idx, score in zip(indices, scores):
            if idx >= 0 and idx < len(self.documents):
                results.append((self.documents[idx], float(score)))

        return results

class NumPyVectorStore:
    """NumPy-backed vector search fallback when FAISS is unavailable on target platform."""
    def __init__(self, embeddings: np.ndarray):
        self.embeddings = embeddings

    def search(self, query_vector: np.ndarray, top_k: int) -> Tuple[np.ndarray, np.ndarray]:
        # Cosine similarity matrix multiplication
        scores = np.dot(self.embeddings, query_vector.T).squeeze()
        if len(scores.shape) == 0:
            scores = np.array([scores])
        top_k_idx = np.argsort(scores)[::-1][:top_k]
        return np.array([scores[top_k_idx]]), np.array([top_k_idx])
