# Project Environment Report

- **Date / Time**: 2026-08-15
- **Operating System**: Windows 10 (x86_64)
- **Python Version**: Python 3.11.9 (`C:\Users\jjape\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe`)
- **Node.js / npm**: Not installed / Not in PATH (using Python FastAPI + HTML5/CSS3/Vanilla JS frontend)
- **Git**: Not in PATH
- **Available Disk Space**: ~86.98 GB
- **Dataset Target**: `ai4bharat/MSMARCO-XI` on Hugging Face
- **Execution Strategy**:
  - Python virtual environment (`venv/`)
  - Fast, modular retrieval with Hugging Face `datasets` (streaming/parquet mode)
  - Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (configurable, CPU/GPU automatic fallback)
  - Vector Database: FAISS (CPU version) / Chroma local storage
  - Backend: FastAPI + Uvicorn + Pydantic
  - Frontend: Responsive single-page web UI (HTML/CSS/JS) with live RAG question answering, streaming status, expandable source passages, and similarity scores.
