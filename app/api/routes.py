import io
import sys
import os
import logging
from fastapi import APIRouter, HTTPException, Query, File, UploadFile
from app.config import config
from app.models.schemas import (
    HealthResponse, SystemInfoResponse, SearchRequest, SearchResponse,
    AskRequest, AskResponse
)
from app.retrieval.retriever import retriever_service
from app.rag.pipeline import rag_pipeline_service
from app.rag.memory import conversation_memory

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    vector_store = retriever_service.vector_store
    index_loaded = vector_store.index is not None or vector_store.load_index()
    total_docs = len(vector_store.documents) if vector_store.documents else 0

    gpu_avail = False
    try:
        import torch
        gpu_avail = torch.cuda.is_available()
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if index_loaded else "degraded",
        python_version=sys.version.split()[0],
        index_loaded=index_loaded,
        total_indexed_documents=total_docs,
        embedding_model=config.EMBEDDING_MODEL,
        stt_provider=config.STT_PROVIDER,
        llm_provider=config.LLM_PROVIDER,
        tts_provider=config.TTS_PROVIDER,
        gpu_available=gpu_avail
    )

@router.get("/api/info", response_model=SystemInfoResponse, tags=["Info"])
def get_system_info():
    return SystemInfoResponse(
        embedding_model=config.EMBEDDING_MODEL,
        stt_provider=config.STT_PROVIDER,
        llm_provider=config.LLM_PROVIDER,
        tts_provider=config.TTS_PROVIDER
    )

@router.post("/api/search", response_model=SearchResponse, tags=["Retrieval"])
def search_passages(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")
    
    results = retriever_service.retrieve(req.query, top_k=req.top_k)
    return SearchResponse(
        query=req.query,
        total_retrieved=len(results),
        results=results
    )

@router.post("/api/ask", response_model=AskResponse, tags=["RAG"])
def ask_question(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        response = rag_pipeline_service.answer_question(req.question, top_k=req.top_k)
        return response
    except Exception as e:
        logger.error(f"Error executing RAG pipeline for question '{req.question}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"RAG pipeline execution failed: {str(e)}")

@router.post("/api/ask-voice", tags=["Voice RAG"])
async def ask_question_voice(file: UploadFile = File(...), top_k: int = Query(5)):
    """Receives binary WAV audio file, transcribes it, runs RAG, and returns audio answer + metadata."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded audio file was empty.")

    audio_io = io.BytesIO(content)
    try:
        response = rag_pipeline_service.answer_question_voice(audio_io, top_k=top_k)
        return response
    except ValueError as ve:
        logger.warning(f"Voice query input error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error executing Voice RAG pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Voice RAG execution failed: {str(e)}")

@router.post("/api/memory/clear", tags=["Memory"])
def clear_conversation_memory():
    conversation_memory.clear()
    return {"message": "Conversation memory cleared successfully."}
