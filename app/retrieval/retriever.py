import logging
from typing import List
from app.config import config
from app.models.schemas import SearchResultItem
from app.retrieval.embeddings import embedding_service
from app.retrieval.vector_store import FAISSVectorStore

logger = logging.getLogger(__name__)

class Retriever:
    def __init__(self, vector_store: FAISSVectorStore = None):
        self.vector_store = vector_store or FAISSVectorStore()

    def retrieve(self, query: str, top_k: int = None) -> List[SearchResultItem]:
        top_k = top_k or config.TOP_K
        if not query or not query.strip():
            return []

        logger.info(f"Retrieving top_{top_k} passages for query: '{query}'")
        query_vector = embedding_service.encode(query, normalize_embeddings=True)
        search_results = self.vector_store.search(query_vector, top_k=top_k)

        items: List[SearchResultItem] = []
        for doc, score in search_results:
            text_content = doc.text
            if doc.metadata and "parent_text" in doc.metadata:
                text_content = doc.metadata["parent_text"]

            items.append(SearchResultItem(
                chunk_id=doc.id,
                query_id=doc.query_id,
                text=text_content,
                score=round(score, 4),
                title=doc.title or "MSMARCO Passage",
                is_relevant=doc.is_relevant,
                source=doc.source
            ))

        return items

retriever_service = Retriever()
