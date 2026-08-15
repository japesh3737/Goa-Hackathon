import os
import json
import shutil
import pickle
import pytest
import faiss
from pathlib import Path
from scripts.build_full_index import IncrementalIndexer
from app.models.schemas import DocumentChunk

@pytest.fixture
def temp_index_dir(tmp_path):
    # Setup temporary directory for index output
    idx_dir = tmp_path / "index"
    idx_dir.mkdir()
    yield idx_dir

def test_checkpoint_creation_and_recovery(temp_index_dir):
    indexer = IncrementalIndexer(temp_index_dir, batch_size=2)
    indexer.index = faiss.IndexFlatIP(384)
    
    # Mock data to process
    dummy_chunks = [
        DocumentChunk(id="c1", query_id="q1", text="First chunk", title="q1"),
        DocumentChunk(id="c2", query_id="q1", text="Second chunk", title="q1")
    ]
    
    indexer.documents.extend(dummy_chunks)
    indexer.processed_count = 10
    indexer.total_chunks = 2
    
    # Save checkpoint
    indexer.save_checkpoint()
    
    assert (temp_index_dir / "checkpoint.json").exists()
    assert (temp_index_dir / "faiss_index.bin").exists()
    assert (temp_index_dir / "metadata.pkl").exists()

    # Recovery check
    resumer = IncrementalIndexer(temp_index_dir)
    loaded = resumer.load_checkpoint_if_exists()
    
    assert loaded
    assert resumer.processed_count == 10
    assert resumer.total_chunks == 2
    assert len(resumer.documents) == 2
    assert resumer.documents[0].id == "c1"

def test_lock_duplicate_prevention(temp_index_dir):
    indexer1 = IncrementalIndexer(temp_index_dir)
    indexer1.acquire_lock()
    
    # Second indexer should raise error
    indexer2 = IncrementalIndexer(temp_index_dir)
    with pytest.raises(RuntimeError) as excinfo:
        indexer2.acquire_lock()
        
    assert "Duplicate Indexing Error" in str(excinfo.value)
    
    indexer1.release_lock()
    # Now it should be able to acquire lock
    indexer2.acquire_lock()
    indexer2.release_lock()

def test_batch_processing(temp_index_dir):
    indexer = IncrementalIndexer(temp_index_dir, batch_size=2)
    indexer.index = faiss.IndexFlatIP(384)
    
    records = [
        {
            "query_id": 100,
            "Eng_Query": "Query Title 1",
            "passages": {
                "English_passages": ["Passage text one.", "Passage text two."],
                "is_selected": [1, 0]
            }
        },
        {
            "query_id": 200,
            "Eng_Query": "Query Title 2",
            "passages": {
                "English_passages": ["Passage text three."],
                "is_selected": [1]
            }
        }
    ]
    
    indexer._process_batch(records)
    
    assert indexer.total_chunks == 3
    assert len(indexer.documents) == 3
    assert indexer.documents[0].id == "100_0"
    assert indexer.documents[0].text == "Passage text one."
    assert indexer.documents[0].title == "Query Title 1"
    assert indexer.documents[2].id == "200_0"
