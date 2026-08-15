import os
import pytest
from app.data.preprocessing import clean_text, chunk_text, process_raw_record
from app.data.dataset_loader import MSMARCODatasetLoader
from app.models.schemas import DocumentChunk

def test_clean_text():
    raw = "  Hello   world! \n\n This is   MSMARCO.  "
    cleaned = clean_text(raw)
    assert cleaned == "Hello world! This is MSMARCO."

def test_chunk_text():
    text = "Word " * 200
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(isinstance(c, str) for c in chunks)

def test_process_raw_record():
    record = {
        "query_id": "q123",
        "title": "Photosynthesis Overview",
        "passages": ["Plants convert light to chemical energy.", "Oxygen is released as a byproduct."]
    }
    chunks = process_raw_record(record)
    assert len(chunks) >= 2
    assert all(isinstance(c, DocumentChunk) for c in chunks)
    assert chunks[0].query_id == "q123"

def test_fallback_sample_generator(tmp_path):
    loader = MSMARCODatasetLoader(sample_size=10)
    sample_file = tmp_path / "sample.parquet"
    loader.create_sample_file(limit=10, output_path=str(sample_file))
    assert sample_file.exists()

    docs = loader.load_processed_sample(str(sample_file))
    assert len(docs) > 0
    assert docs[0].source is not None
