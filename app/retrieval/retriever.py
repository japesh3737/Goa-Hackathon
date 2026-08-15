import re
import math
import logging
import numpy as np
from typing import List, Tuple, Dict, Any
from app.config import config
from app.models.schemas import SearchResultItem, DocumentChunk
from app.retrieval.embeddings import embedding_service
from app.retrieval.vector_store import FAISSVectorStore

logger = logging.getLogger(__name__)

def tokenize(text: str) -> List[str]:
    return re.findall(r'\w+', text.lower())

class BM25Index:
    """Fast, in-memory BM25 index for keyword & entity matching."""
    def __init__(self):
        self.doc_freqs: List[Dict[str, int]] = []
        self.df: Dict[str, int] = {}
        self.doc_len: List[int] = []
        self.avg_doc_len: float = 1.0
        self.total_docs: int = 0

    def fit(self, corpus_texts: List[str]):
        self.total_docs = len(corpus_texts)
        self.doc_len = [len(tokenize(d)) for d in corpus_texts]
        self.avg_doc_len = sum(self.doc_len) / self.total_docs if self.total_docs > 0 else 1.0
        self.doc_freqs = []
        self.df = {}

        for d in corpus_texts:
            freqs = {}
            for w in tokenize(d):
                freqs[w] = freqs.get(w, 0) + 1
            self.doc_freqs.append(freqs)
            for w in freqs:
                self.df[w] = self.df.get(w, 0) + 1

    def score(self, query: str, k1: float = 1.5, b: float = 0.75) -> np.ndarray:
        if not self.total_docs:
            return np.zeros(0)

        q_tokens = tokenize(query)
        scores = np.zeros(self.total_docs, dtype=np.float32)
        N = self.total_docs

        for idx, freqs in enumerate(self.doc_freqs):
            score = 0.0
            for w in q_tokens:
                if w in freqs:
                    tf = freqs[w]
                    df = self.df.get(w, 0)
                    idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
                    doc_len = self.doc_len[idx]
                    denom = tf + k1 * (1.0 - b + b * (doc_len / self.avg_doc_len))
                    score += idf * (tf * (k1 + 1.0)) / denom
            scores[idx] = score

        return scores

class HybridRetriever:
    """
    State-of-the-art Hybrid Retriever combining:
    1. Dense Vector Retrieval via FAISS (sentence-transformers cosine similarity)
    2. BM25 Lexical Keyword & Entity Retrieval
    Blends normalized scores with Reciprocal Rank Fusion / Alpha-weighting for maximum precision.
    """
    def __init__(self, vector_store: FAISSVectorStore = None):
        self.vector_store = vector_store or FAISSVectorStore()
        self.bm25 = BM25Index()
        self._bm25_initialized = False

    def _ensure_bm25_index(self):
        if self._bm25_initialized and self.bm25.total_docs == len(self.vector_store.documents):
            return

        if not self.vector_store.documents:
            self.vector_store.load_index()

        if self.vector_store.documents:
            corpus_texts = [
                f"{doc.title} {doc.text}" for doc in self.vector_store.documents
            ]
            self.bm25.fit(corpus_texts)
            self._bm25_initialized = True

    def retrieve(self, query: str, top_k: int = None, alpha: float = 0.55) -> List[SearchResultItem]:
        """
        Hybrid retrieval combining BM25 keyword score (alpha) and Dense FAISS cosine score (1 - alpha).
        """
        top_k = top_k or config.TOP_K
        if not query or not query.strip():
            return []

        self._ensure_bm25_index()
        docs = self.vector_store.documents
        if not docs:
            return []

        # 1. Dense Semantic Embeddings (FAISS)
        query_vector = embedding_service.encode(query, normalize_embeddings=True).flatten()
        dense_results = self.vector_store.search(query_vector, top_k=len(docs))
        dense_score_map = {doc.id: score for doc, score in dense_results}

        # 2. BM25 Lexical Keyword Scores
        bm25_scores = self.bm25.score(query)
        max_bm25 = np.max(bm25_scores) if len(bm25_scores) > 0 and np.max(bm25_scores) > 0 else 1.0
        bm25_norm = bm25_scores / max_bm25 if max_bm25 > 0 else bm25_scores

        # 3. Hybrid Fusion
        scored_items: List[Tuple[DocumentChunk, float]] = []
        for idx, doc in enumerate(docs):
            bm_score = float(bm25_norm[idx])
            dense_score = float(dense_score_map.get(doc.id, 0.0))

            # Dynamic weighting: if exact keyword matches exist, boost BM25; otherwise rely on dense semantics
            if bm_score > 0.05:
                hybrid_score = (alpha * bm_score) + ((1.0 - alpha) * max(0.0, dense_score))
            else:
                hybrid_score = dense_score

            scored_items.append((doc, hybrid_score))

        # Sort by hybrid score descending
        scored_items.sort(key=lambda x: x[1], reverse=True)

        # Deduplicate identical texts from redundant sample copies
        seen_texts = set()
        unique_results = []
        for doc, score in scored_items:
            # Normalize text for deduping
            text_key = doc.text.strip()[:120].lower()
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                unique_results.append((doc, score))
            if len(unique_results) >= top_k:
                break

        # Convert to SearchResultItem schemas
        items: List[SearchResultItem] = []
        for doc, score in unique_results:
            text_content = doc.text
            if doc.metadata and "parent_text" in doc.metadata:
                text_content = doc.metadata["parent_text"]

            items.append(SearchResultItem(
                chunk_id=doc.id,
                query_id=doc.query_id,
                text=text_content,
                score=round(float(score), 4),
                title=doc.title or "MSMARCO Passage",
                is_relevant=doc.is_relevant,
                source=doc.source
            ))

        return items

# Alias for backward compatibility
Retriever = HybridRetriever
retriever_service = HybridRetriever()
