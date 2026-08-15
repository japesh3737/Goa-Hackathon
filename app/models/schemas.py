from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    id: str = Field(..., description="Unique chunk identifier")
    query_id: str = Field(..., description="Original query ID from MSMARCO-XI")
    text: str = Field(..., description="Passage text")
    title: Optional[str] = Field(default="", description="Document title if available")
    source: str = Field(default="MSMARCO-XI", description="Dataset source")
    is_relevant: bool = Field(default=True, description="Whether labeled relevant for original query")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional document metadata")


class SearchRequest(BaseModel):
    query: str = Field(..., description="User search query", example="What is photosynthesis?")
    top_k: Optional[int] = Field(default=5, ge=1, le=50, description="Number of passages to retrieve")


class SearchResultItem(BaseModel):
    chunk_id: str
    query_id: str
    text: str
    score: float
    title: Optional[str] = ""
    is_relevant: Optional[bool] = None
    source: str = "MSMARCO-XI"


class SearchResponse(BaseModel):
    query: str
    total_retrieved: int
    results: List[SearchResultItem]


class AskRequest(BaseModel):
    question: str = Field(..., description="User question", example="How does plant photosynthesis work?")
    top_k: Optional[int] = Field(default=5, ge=1, le=50, description="Number of context passages")


class SourcePassage(BaseModel):
    id: str
    score: float
    text: str
    query_id: str
    title: Optional[str] = ""


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourcePassage]
    retrieved_documents: List[SearchResultItem]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    python_version: str
    index_loaded: bool
    total_indexed_documents: int
    embedding_model: str
    stt_provider: str
    llm_provider: str
    tts_provider: str
    gpu_available: bool


class SystemInfoResponse(BaseModel):
    app_name: str = "MSMARCO-XI English Voice RAG Agent"
    version: str = "1.0.0"
    dataset: str = "ai4bharat/MSMARCO-XI"
    embedding_model: str
    vector_store: str = "FAISS (Local Persisted)"
    stt_provider: str
    llm_provider: str
    tts_provider: str
