import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "embedding_model" in data

def test_info_endpoint():
    response = client.get("/api/info")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "MSMARCO-XI English Voice RAG Agent"

def test_search_endpoint():
    response = client.post("/api/search", json={"query": "photosynthesis", "top_k": 3})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "photosynthesis"
    assert "results" in data

def test_ask_endpoint(monkeypatch):
    from app.rag.pipeline import rag_pipeline_service
    from app.rag.answer_generator import MockGroundedLLMProvider
    monkeypatch.setattr(rag_pipeline_service, "llm_provider", MockGroundedLLMProvider())

    response = client.post("/api/ask", json={"question": "What is Python?", "top_k": 2})
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "What is Python?"
    assert "answer" in data
    assert "sources" in data
