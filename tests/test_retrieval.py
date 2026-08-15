import pytest
import numpy as np
from app.retrieval.embeddings import embedding_service
from app.retrieval.vector_store import FAISSVectorStore
from app.retrieval.retriever import Retriever
from app.models.schemas import DocumentChunk

def test_embeddings_service():
    text = "Query embedding test"
    vec = embedding_service.encode(text)
    assert isinstance(vec, np.ndarray)
    assert vec.shape[0] == 1
    assert vec.shape[1] > 0

def test_vector_store_build_and_search(tmp_path):
    docs = [
        DocumentChunk(id="c1", query_id="q1", text="Photosynthesis is light conversion in plants.", title="Botany"),
        DocumentChunk(id="c2", query_id="q2", text="Python is a computer programming language.", title="Computer Science"),
        DocumentChunk(id="c3", query_id="q3", text="Deep learning RAG systems use vector retrieval.", title="AI")
    ]

    idx_file = tmp_path / "faiss.bin"
    meta_file = tmp_path / "meta.pkl"
    vs = FAISSVectorStore(index_path=str(idx_file), metadata_path=str(meta_file))
    vs.build_index(docs)

    assert idx_file.exists()
    assert meta_file.exists()

    query_vec = embedding_service.encode("Tell me about Python programming")
    results = vs.search(query_vec, top_k=2)

    assert len(results) == 2
    top_doc, score = results[0]
    assert top_doc.id == "c2" # Should match Python passage best
    assert score > 0.0

def test_retriever_search():
    retriever = Retriever()
    # Test fallback graceful handling if empty query
    res = retriever.retrieve("", top_k=5)
    assert res == []
