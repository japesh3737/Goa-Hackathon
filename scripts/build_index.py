import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.dataset_loader import MSMARCODatasetLoader
from app.retrieval.vector_store import FAISSVectorStore

if __name__ == "__main__":
    print("=== Building Vector Index from MSMARCO-XI Sample Data ===")
    loader = MSMARCODatasetLoader()
    documents = loader.load_processed_sample()
    print(f"Loaded {len(documents)} document chunks for indexing.")

    vector_store = FAISSVectorStore()
    vector_store.build_index(documents)
    print("Vector index built and persisted successfully!")
