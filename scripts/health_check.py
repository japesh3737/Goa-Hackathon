import sys
import os
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def check_health():
    print("=== MSMARCO-XI RAG Agent System Health Check ===")
    checks = {}

    # 1. Python Environment
    checks["Python Environment"] = sys.version_info >= (3, 9)

    # 2. Required Packages
    required = ["fastapi", "uvicorn", "pydantic", "datasets", "sentence_transformers", "faiss", "pandas", "speech_recognition", "gtts"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
    checks["Required Packages"] = len(missing) == 0

    # 3. Local Sample Data
    from app.config import config
    checks["Processed Sample Data"] = config.PROCESSED_DATA_PATH.exists()

    # 4. Vector Index & Metadata Store
    checks["Vector Index Persisted"] = config.VECTOR_STORE_PATH.exists() and config.METADATA_STORE_PATH.exists()

    # 5. Embedding Model Load
    try:
        from app.retrieval.embeddings import embedding_service
        vec = embedding_service.encode("health check test query")
        checks["Embedding Model Active"] = vec.shape[0] == 1 and vec.shape[1] > 0
    except Exception:
        checks["Embedding Model Active"] = False

    # 6. RAG Pipeline Initialization
    try:
        from app.rag.pipeline import rag_pipeline_service
        checks["RAG Pipeline Initialized"] = rag_pipeline_service is not None
    except Exception:
        checks["RAG Pipeline Initialized"] = False

    # 7. Local API Server Health (if running)
    try:
        resp = requests.get(f"http://127.0.0.1:{config.API_PORT}/health", timeout=2)
        checks["Local API Server Running"] = resp.status_code == 200
    except Exception:
        checks["Local API Server Running"] = False # Optional if server not started yet

    # Display status
    print("\nHealth Status Checklist:")
    all_passed = True
    for key, status in checks.items():
        symbol = "[PASS]" if status else ("[FAIL]" if key != "Local API Server Running" else "[OFFLINE]")
        if not status and key != "Local API Server Running":
            all_passed = False
        print(f"  {symbol:<10} {key}")

    print("\nOverall System Readiness:", "PASS" if all_passed else "DEGRADED/ACTION REQUIRED")
    return all_passed

if __name__ == "__main__":
    check_health()
