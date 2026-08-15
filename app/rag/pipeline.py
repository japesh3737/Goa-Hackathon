import io
import time
import base64
import logging
from typing import Dict, Any, List
from app.config import config
from app.retrieval.retriever import retriever_service
from app.retrieval.audio_stt import get_stt_provider
from app.rag.audio_tts import get_tts_provider
from app.rag.answer_generator import get_llm_provider
from app.rag.memory import conversation_memory
from app.rag.cache import rag_cache
from app.rag.harness import rag_harness
from app.models.schemas import AskResponse, SourcePassage, SearchResultItem

logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        self.retriever = retriever_service
        self.llm_provider = get_llm_provider()
        self.stt_provider = get_stt_provider()
        self.tts_provider = get_tts_provider()

    def answer_question(self, question: str, top_k: int = None) -> AskResponse:
        """Standard Text Fallback RAG Pipeline with memory context and caching."""
        top_k = top_k or config.TOP_K
        start_time = time.time()

        # Step 0: Check text cache
        cached = rag_cache.get(question)
        if cached:
            sources = [
                SourcePassage(**s) if isinstance(s, dict) else s 
                for s in cached.get("sources", [])
            ]
            retrieved = [
                SearchResultItem(**d) if isinstance(d, dict) else d 
                for d in cached.get("retrieved_documents", [])
            ]
            logger.info(f"Cache HIT for query: '{question}'")
            return AskResponse(
                question=question,
                answer=cached.get("answer", ""),
                sources=sources,
                retrieved_documents=retrieved,
                metadata={
                    "cached": True,
                    "total_time_sec": round(time.time() - start_time, 4),
                    "retrieval_time_sec": 0.0,
                    "generation_time_sec": 0.0,
                    "top_k": top_k,
                    "llm_provider": config.LLM_PROVIDER,
                    "embedding_model": config.EMBEDDING_MODEL
                }
            )

        # Step 1: Retrieval
        retrieval_start = time.time()
        retrieved_docs = self.retriever.retrieve(question, top_k=top_k)
        retrieval_time = time.time() - retrieval_start

        # Step 2: Get memory history context
        history_context = conversation_memory.get_formatted_history()

        # Step 3: Grounded Answer Generation via Harness (orchestrated & guarded)
        gen_start = time.time()
        harness_res = rag_harness.process_query(question, retrieved_docs, history_context)
        answer = harness_res["answer"]
        gen_time = time.time() - gen_start

        # Step 4: Update Conversation Memory
        conversation_memory.add_turn(question, answer)

        total_time = time.time() - start_time

        # Format sources
        sources = [
            SourcePassage(
                id=doc.chunk_id,
                score=doc.score,
                text=doc.text,
                query_id=doc.query_id,
                title=doc.title
            )
            for doc in retrieved_docs
        ]

        meta = {
            "cached": False,
            "retrieval_time_sec": round(retrieval_time, 4),
            "generation_time_sec": round(gen_time, 4),
            "total_time_sec": round(total_time, 4),
            "top_k": top_k,
            "llm_provider": config.LLM_PROVIDER,
            "embedding_model": config.EMBEDDING_MODEL,
            "is_relevant": harness_res.get("is_relevant", True),
            "is_safe": harness_res.get("is_safe", True),
            "is_grounded": harness_res.get("is_grounded", True),
            "confidence_score": harness_res.get("confidence_score", 1.0)
        }

        response_obj = AskResponse(
            question=question,
            answer=answer,
            sources=sources,
            retrieved_documents=retrieved_docs,
            metadata=meta
        )

        # Cache text-only result
        rag_cache.set(question, {
            "answer": answer,
            "sources": [s.model_dump() for s in sources],
            "retrieved_documents": [doc.model_dump() for doc in retrieved_docs]
        })

        return response_obj

    def answer_question_voice(self, audio_data: io.BytesIO, top_k: int = None) -> Dict[str, Any]:
        """Speech Input -> STT -> RAG Retrieval -> LLM -> TTS -> Audio Output Pipeline with cache checks."""
        top_k = top_k or config.TOP_K
        start_time = time.time()

        # Step 1: Speech-To-Text Transcription
        stt_start = time.time()
        transcript = self.stt_provider.transcribe(audio_data)
        stt_time = time.time() - stt_start

        if not transcript or not transcript.strip():
            raise ValueError("No speech detected or transcription was empty.")

        # Step 2: Check voice cache
        cached = rag_cache.get(transcript)
        if cached and "audio" in cached:
            total_time = time.time() - start_time
            logger.info(f"Voice Cache HIT for transcript: '{transcript}'")
            return {
                "transcript": transcript,
                "answer": cached["answer"],
                "sources": cached["sources"],
                "retrieved_documents": cached["retrieved_documents"],
                "audio": cached["audio"],
                "metadata": {
                    "cached": True,
                    "stt_time_sec": round(stt_time, 4),
                    "retrieval_time_sec": 0.0,
                    "generation_time_sec": 0.0,
                    "tts_time_sec": 0.0,
                    "total_time_sec": round(total_time, 4),
                    "top_k": top_k,
                    "llm_provider": config.LLM_PROVIDER,
                    "stt_provider": config.STT_PROVIDER,
                    "tts_provider": config.TTS_PROVIDER
                }
            }

        # Step 3: Run standard RAG Text Pipeline
        rag_response = self.answer_question(transcript, top_k=top_k)

        # Step 4: Text-To-Speech Synthesis
        tts_start = time.time()
        audio_content = self.tts_provider.synthesize(rag_response.answer)
        tts_time = time.time() - tts_start

        # Step 5: Encode audio output to Base64 (MP3 format)
        audio_b64 = base64.b64encode(audio_content).decode("utf-8")
        audio_url = f"data:audio/mp3;base64,{audio_b64}"
        total_time = time.time() - start_time

        res = {
            "transcript": transcript,
            "answer": rag_response.answer,
            "sources": [s.model_dump() for s in rag_response.sources],
            "retrieved_documents": [doc.model_dump() for doc in rag_response.retrieved_documents],
            "audio": audio_url,
            "metadata": {
                "cached": False,
                "stt_time_sec": round(stt_time, 4),
                "retrieval_time_sec": rag_response.metadata.get("retrieval_time_sec", 0.0),
                "generation_time_sec": rag_response.metadata.get("generation_time_sec", 0.0),
                "tts_time_sec": round(tts_time, 4),
                "total_time_sec": round(total_time, 4),
                "top_k": top_k,
                "llm_provider": config.LLM_PROVIDER,
                "stt_provider": config.STT_PROVIDER,
                "tts_provider": config.TTS_PROVIDER
            }
        }

        # Cache voice result (includes base64 audio payload)
        rag_cache.set(transcript, res)

        return res

rag_pipeline_service = RAGPipeline()
