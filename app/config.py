import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    # Dataset Settings
    DATASET_NAME: str = os.getenv("DATASET_NAME", "ai4bharat/MSMARCO-XI")
    DATASET_CONFIG: str = os.getenv("DATASET_CONFIG", "default")
    DATASET_SPLIT: str = os.getenv("DATASET_SPLIT", "train")
    SAMPLE_SIZE: int = int(os.getenv("SAMPLE_SIZE", "500"))

    # Embeddings & Retrieval Settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    TOP_K: int = int(os.getenv("TOP_K", "5"))

    # File Paths
    DATA_DIR: Path = BASE_DIR / "data"
    PROCESSED_DATA_PATH: Path = BASE_DIR / os.getenv("PROCESSED_DATA_PATH", "data/processed/english_sample.parquet")
    
    INDEX_MODE: str = os.getenv("INDEX_MODE", "dev").lower()
    
    @property
    def VECTOR_STORE_PATH(self) -> Path:
        self._migrate_dev_index()
        subfolder = "full" if self.INDEX_MODE == "full" else "dev"
        return self.DATA_DIR / "index" / subfolder / "faiss_index.bin"
        
    @property
    def METADATA_STORE_PATH(self) -> Path:
        subfolder = "full" if self.INDEX_MODE == "full" else "dev"
        return self.DATA_DIR / "index" / subfolder / "metadata.pkl"

    def _migrate_dev_index(self):
        """Helper to move the old top-level dev index to the data/index/dev/ folder if needed."""
        dev_dir = self.DATA_DIR / "index" / "dev"
        old_bin = self.DATA_DIR / "index" / "faiss_index.bin"
        old_pkl = self.DATA_DIR / "index" / "metadata.pkl"
        
        if old_bin.exists() and not (dev_dir / "faiss_index.bin").exists():
            import shutil
            dev_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(old_bin, dev_dir / "faiss_index.bin")
            if old_pkl.exists():
                shutil.copy(old_pkl, dev_dir / "metadata.pkl")

    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Voice Settings
    STT_PROVIDER: str = os.getenv("STT_PROVIDER", "google")
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "gtts")
    MEMORY_WINDOW: int = int(os.getenv("MEMORY_WINDOW", "3"))

    # Third-party Speech Keys
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")

    # Chunking Strategy Configuration
    # Options: fixed, recursive, semantic, parent_child
    CHUNK_STRATEGY: str = os.getenv("CHUNK_STRATEGY", "recursive").lower()

    # API Settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

config = Config()
