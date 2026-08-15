import pytest
from app.rag.prompts import build_rag_prompt
from app.rag.answer_generator import MockGroundedLLMProvider, get_llm_provider
from app.rag.pipeline import RAGPipeline
from app.models.schemas import SearchResultItem

def test_build_rag_prompt():
    docs = [SearchResultItem(chunk_id="d1", query_id="q1", text="Sample text", score=0.95)]
    prompt = build_rag_prompt("Test question", docs)
    assert "Test question" in prompt
    assert "d1" in prompt
    assert "Sample text" in prompt

def test_mock_grounded_llm_provider():
    provider = MockGroundedLLMProvider()
    docs = [SearchResultItem(chunk_id="doc_10", query_id="q10", text="FastAPI is a fast web framework.", score=0.88)]
    ans = provider.generate("What is FastAPI?", docs)
    assert "FastAPI" in ans
    assert "[doc_10]" in ans

def test_rag_pipeline_execution(tmp_path, monkeypatch):
    pipeline = RAGPipeline()
    monkeypatch.setattr(pipeline, "llm_provider", MockGroundedLLMProvider())
    res = pipeline.answer_question("What is photosynthesis?", top_k=3)
    assert res.question == "What is photosynthesis?"
    assert res.answer is not None
    assert isinstance(res.sources, list)
    assert "total_time_sec" in res.metadata
