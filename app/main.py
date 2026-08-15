import os
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import config
from app.api.routes import router
from app.retrieval.retriever import retriever_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MSMARCO-XI English RAG Agent API",
    description="Production-grade Retrieval-Augmented Generation API powered by AI4Bharat MSMARCO-XI dataset.",
    version="1.0.0"
)

# Enable CORS for local dev / frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API endpoints
app.include_router(router)

# Mount Frontend static files
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

@app.get("/")
@app.get("/chat")
@app.get("/voice")
def read_root():
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "MSMARCO-XI RAG Agent API is active. Open /docs for Swagger API documentation."}

@app.on_event("startup")
def startup_event():
    logger.info("Initializing MSMARCO-XI RAG Agent backend...")
    loaded = retriever_service.vector_store.load_index()
    if loaded:
        logger.info(f"Loaded vector store with {len(retriever_service.vector_store.documents)} items.")
    else:
        logger.warning("No pre-existing vector store found. Run 'python scripts/build_index.py' to generate index.")

    try:
        from app.retrieval.embeddings import embedding_service
        logger.info("Pre-warming embedding model sentence-transformers...")
        embedding_service.encode("warmup query")
        logger.info("Embedding model successfully warmed up!")
    except Exception as e:
        logger.error(f"Failed to pre-warm embedding model: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=config.API_HOST, port=config.API_PORT, reload=True)
