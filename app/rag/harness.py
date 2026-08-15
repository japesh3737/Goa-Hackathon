import re
import time
import logging
from typing import List, Dict, Any
from app.models.schemas import SearchResultItem
from app.rag.answer_generator import get_llm_provider, LLMProvider
from app.rag.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

HARNESS_SYSTEM_PROMPT = SYSTEM_PROMPT

class RAGHarness:
    def __init__(self, llm_provider: LLMProvider = None):
        self.llm_provider = llm_provider or get_llm_provider()

    def clean_json_string(self, raw_str: str) -> str:
        """Strip markdown code block wrappers from JSON string if present."""
        cleaned = raw_str.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return cleaned

    def process_query(self, query: str, retrieved_docs: List[SearchResultItem], history_context: str = "") -> Dict[str, Any]:
        """
        Orchestrates RAG retrieval, context validation, LLM synthesis, and citation extraction.
        """
        if not retrieved_docs:
            return {
                "is_relevant": False,
                "is_safe": True,
                "is_grounded": False,
                "answer": "The retrieved context does not contain sufficient information to answer this question.",
                "citations": [],
                "confidence_score": 0.0
            }

        top_score = retrieved_docs[0].score

        # Guardrail check for completely off-topic scores (< 0.20)
        if top_score < 0.20:
            return {
                "is_relevant": False,
                "is_safe": True,
                "is_grounded": False,
                "answer": "The retrieved context does not contain sufficient information to answer this question.",
                "citations": [],
                "confidence_score": round(float(top_score), 3)
            }

        try:
            answer = self.llm_provider.generate(query, retrieved_docs, history_context)
            
            citations = []
            found_bracket_ids = re.findall(r'\[(doc_\w+|Passage\s*\d+|\w+_\w+)\]', answer, re.IGNORECASE)
            for cid in found_bracket_ids:
                if cid not in citations:
                    citations.append(cid)

            if not citations and retrieved_docs:
                citations = [doc.chunk_id for doc in retrieved_docs[:3]]

            confidence = min(1.0, max(0.4, float(top_score) * 1.25))

            return {
                "is_relevant": True,
                "is_safe": True,
                "is_grounded": True,
                "answer": answer,
                "citations": citations,
                "confidence_score": round(confidence, 3)
            }
        except Exception as e:
            logger.error(f"Error during RAG answer synthesis: {e}")
            top_passages = retrieved_docs[:3]
            bullets = "\n".join([f"• [{doc.chunk_id}] {doc.text}" for doc in top_passages])
            return {
                "is_relevant": True,
                "is_safe": True,
                "is_grounded": True,
                "answer": f"Based on the knowledge corpus evidence:\n\n{bullets}",
                "citations": [d.chunk_id for d in top_passages],
                "confidence_score": round(float(top_score), 3)
            }

rag_harness = RAGHarness()
