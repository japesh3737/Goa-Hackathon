import io
import pytest
from app.config import config
from app.data.preprocessing import recursive_character_split, semantic_split, process_raw_record
from app.rag.cache import RAGCache, rag_cache
from app.rag.harness import RAGHarness, HARNESS_SYSTEM_PROMPT
from app.models.schemas import SearchResultItem
from app.retrieval.audio_stt import get_stt_provider, ElevenLabsSTTProvider, SarvamSTTProvider

def test_recursive_character_split():
    text = "This is a sentence. This is another sentence. This is a third sentence."
    # With a small chunk size, it should split
    chunks = recursive_character_split(text, chunk_size=30, chunk_overlap=5)
    assert len(chunks) > 1
    assert all(len(c) <= 40 for c in chunks)

def test_semantic_split():
    text = "Photosynthesis converts light to energy. Plants use chloroplasts. Python is a programming language."
    chunks = semantic_split(text)
    assert len(chunks) >= 1

def test_parent_child_chunking_metadata():
    # Set config strategy to parent_child
    original_strategy = config.CHUNK_STRATEGY
    config.CHUNK_STRATEGY = "parent_child"
    
    record = {
        "query_id": "test_q",
        "text": "This is a long passage designed to verify the parent-child chunk mapping strategy. It should split this text into parent sections, then generate smaller child chunks referencing the parent text in their metadata.",
        "title": "Test Document"
    }
    
    chunks = process_raw_record(record)
    assert len(chunks) > 0
    # Every chunk should have parent_text in its metadata
    for chunk in chunks:
        assert "parent_text" in chunk.metadata
        assert len(chunk.text) < len(chunk.metadata["parent_text"])
        assert chunk.title == "Test Document"
        
    # Restore original strategy
    config.CHUNK_STRATEGY = original_strategy

def test_rag_cache():
    cache = RAGCache(cache_file="data/processed/test_rag_cache.json")
    cache.clear()
    
    test_query = "What is Python?"
    test_response = {"answer": "Python is a language.", "sources": [], "retrieved_documents": []}
    
    # Get should return None
    assert cache.get(test_query) is None
    
    # Set and Get
    cache.set(test_query, test_response)
    cached = cache.get(test_query)
    assert cached is not None
    assert cached["answer"] == "Python is a language."
    
    # Case insensitivity & trailing punctuation stripping
    assert cache.get("what is python") is not None
    assert cache.get("What is Python?") is not None
    assert cache.get("WHAT IS PYTHON!!!") is not None
    
    cache.clear()
    assert cache.get(test_query) is None

def test_rag_harness_json_cleaning():
    harness = RAGHarness()
    raw_md_json = "```json\n{\n  \"answer\": \"hello\"\n}\n```"
    cleaned = harness.clean_json_string(raw_md_json)
    assert cleaned == "{\n  \"answer\": \"hello\"\n}"

def test_rag_harness_off_topic_guardrail():
    harness = RAGHarness()
    # Mock retrieved doc with low similarity score (<0.20)
    low_score_doc = SearchResultItem(
        chunk_id="doc_1",
        query_id="q_1",
        text="FastAPI is a python framework.",
        score=0.15,
        title="FastAPI"
    )
    
    res = harness.process_query("How do I cook pasta?", [low_score_doc])
    assert res["is_relevant"] is False
    assert "context" in res["answer"].lower() or "dataset" in res["answer"].lower()

def test_stt_provider_selection():
    # ElevenLabs
    el_stt = get_stt_provider("elevenlabs")
    assert isinstance(el_stt, ElevenLabsSTTProvider)
    
    # Sarvam
    sa_stt = get_stt_provider("sarvam")
    assert isinstance(sa_stt, SarvamSTTProvider)
