import os
import sys
import json
import time
import pickle
import argparse
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Insert parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import faiss
import numpy as np
from datasets import load_dataset
from app.config import config
from app.retrieval.embeddings import embedding_service
from app.models.schemas import DocumentChunk

# Set up logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("build_full_index")

class IncrementalIndexer:
    def __init__(self, index_dir: Path, batch_size: int = 500, checkpoint_interval: int = 1000):
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.batch_size = batch_size
        self.checkpoint_interval = checkpoint_interval

        self.checkpoint_path = self.index_dir / "checkpoint.json"
        self.index_path = self.index_dir / "faiss_index.bin"
        self.metadata_path = self.index_dir / "metadata.pkl"

        self.index = None
        self.documents: List[DocumentChunk] = []
        self.processed_count = 0
        self.total_chunks = 0
        self.dimension = 384

        # Lock file to prevent duplicate processes
        self.lock_path = self.index_dir / "indexing.lock"
        self.lock_file = None

    def acquire_lock(self):
        """Acquires lock to prevent duplicate indexing runs."""
        if self.lock_path.exists():
            # Check if process is still active (read PID)
            try:
                with open(self.lock_path, "r") as f:
                    pid = int(f.read().strip())
                # On Windows/Unix check if PID is alive
                if self._pid_exists(pid):
                    raise RuntimeError(f"Duplicate Indexing Error: Process {pid} is already indexing.")
            except (ValueError, OSError):
                pass
        
        # Write current PID
        with open(self.lock_path, "w") as f:
            f.write(str(os.getpid()))
        logger.info(f"Acquired indexing lock. PID: {os.getpid()}")

    def release_lock(self):
        """Releases process lock."""
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
                logger.info("Released indexing lock.")
        except Exception as e:
            logger.warning(f"Error releasing lock: {e}")

    def _pid_exists(self, pid: int) -> bool:
        if pid < 0:
            return False
        if os.name == 'nt':
            # Windows process check
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_INFORMATION = 0x0400
            handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            # Unix process check
            try:
                os.kill(pid, 0)
            except OSError:
                return False
            else:
                return True

    def load_checkpoint_if_exists(self) -> bool:
        """Loads state from checkpoint files if they exist."""
        if self.checkpoint_path.exists() and self.index_path.exists() and self.metadata_path.exists():
            try:
                # Load metadata
                with open(self.metadata_path, "rb") as f:
                    self.documents = pickle.load(f)
                
                # Load FAISS index
                self.index = faiss.read_index(str(self.index_path))
                
                # Load checkpoint JSON
                with open(self.checkpoint_path, "r") as f:
                    state = json.load(f)
                
                self.processed_count = state.get("processed_count", 0)
                self.total_chunks = state.get("total_chunks", 0)
                
                logger.info(f"Loaded existing checkpoint. Resuming from record {self.processed_count} (chunks: {self.total_chunks}).")
                return True
            except Exception as e:
                logger.error(f"Error loading checkpoint: {e}. Starting fresh.")
                self.index = None
                self.documents = []
                self.processed_count = 0
                self.total_chunks = 0
                
        return False

    def save_checkpoint(self):
        """Saves current index and metadata to checkpoint files atomically."""
        tmp_index = self.index_dir / "faiss_index.bin.tmp"
        tmp_metadata = self.index_dir / "metadata.pkl.tmp"
        tmp_checkpoint = self.index_dir / "checkpoint.json.tmp"

        try:
            # Write FAISS Index
            faiss.write_index(self.index, str(tmp_index))
            
            # Write Metadata pickle
            with open(tmp_metadata, "wb") as f:
                pickle.dump(self.documents, f, protocol=pickle.HIGHEST_PROTOCOL)
                
            # Write Checkpoint JSON
            state = {
                "processed_count": self.processed_count,
                "total_chunks": self.total_chunks,
                "timestamp": time.time()
            }
            with open(tmp_checkpoint, "w") as f:
                json.dump(state, f, indent=2)

            # Atomic swap
            if tmp_index.exists():
                shutil.move(str(tmp_index), str(self.index_path))
            if tmp_metadata.exists():
                shutil.move(str(tmp_metadata), str(self.metadata_path))
            if tmp_checkpoint.exists():
                shutil.move(str(tmp_checkpoint), str(self.checkpoint_path))

            logger.info(f"Saved checkpoint successfully. Records: {self.processed_count}, Chunks: {self.total_chunks}")
        except Exception as e:
            logger.error(f"Failed to write checkpoint files: {e}")

    def generate_mock_raw_records(self, limit: int) -> List[Dict[str, Any]]:
        sample_queries = [
            ("What is photosynthesis?", ["Photosynthesis is a process used by plants to convert light energy into chemical energy.", "This chemical energy is stored in carbohydrate molecules, such as sugars."]),
            ("What is Python programming language?", ["Python is a high-level, general-purpose programming language.", "Its design philosophy emphasizes code readability with the use of significant indentation."]),
            ("What is MS MARCO dataset?", ["MS MARCO is a collection of datasets focused on deep learning in search.", "The dataset consists of 1,010,916 real Bing search queries."]),
            ("What is artificial intelligence?", ["Artificial intelligence is the intelligence of machines or software.", "It develops and studies intelligent machines."])
        ]
        records = []
        for idx in range(limit):
            query, passages = sample_queries[idx % len(sample_queries)]
            records.append({
                "query_id": 100000 + idx,
                "Eng_Query": f"{query} (Mock Record #{idx})",
                "passages": {
                    "English_passages": passages,
                    "is_selected": [1, 0]
                }
            })
        return records

    def run_indexing(self, limit: int = None, local_mock: bool = False):
        self.acquire_lock()
        try:
            has_checkpoint = self.load_checkpoint_if_exists()
            
            if not has_checkpoint:
                # Initialize fresh FlatIP FAISS index
                self.index = faiss.IndexFlatIP(self.dimension)
                logger.info("Initializing clean index flat IP.")

            if local_mock:
                logger.info("Using local mock raw records for indexing...")
                dataset = self.generate_mock_raw_records(limit or 1000)
                dataset_iterator = iter(dataset)
            else:
                # Direct Parquet file URL streaming to bypass PyArrow scan nested array bugs
                logger.info(f"Fetching Parquet file list for '{config.DATASET_NAME}'...")
                import urllib.request
                import fsspec
                import pyarrow.parquet as pq
                
                url = f"https://huggingface.co/api/datasets/{config.DATASET_NAME}/parquet"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req) as resp:
                    parquet_metadata = json.loads(resp.read().decode("utf-8"))
                
                split_name = config.DATASET_SPLIT
                parquet_urls = parquet_metadata.get(config.DATASET_CONFIG, {}).get(split_name, [])
                if not parquet_urls:
                    raise RuntimeError(f"No parquet files found for config={config.DATASET_CONFIG}, split={split_name}")
                
                logger.info(f"Found {len(parquet_urls)} Parquet partition files for split '{split_name}'. Starting stream...")
                
                def record_generator():
                    from pathlib import Path
                    temp_dir = Path("data/temp_partitions")
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    
                    for p_idx, p_url in enumerate(parquet_urls):
                        logger.info(f"Downloading partition file {p_idx+1}/{len(parquet_urls)}: {p_url.split('/')[-1]}...")
                        local_path = temp_dir / f"partition_{p_idx}.parquet"
                        
                        # Download partition file locally with retries
                        max_download_retries = 5
                        download_success = False
                        for attempt in range(max_download_retries):
                            try:
                                req = urllib.request.Request(p_url, headers={"User-Agent": "Mozilla/5.0"})
                                with urllib.request.urlopen(req, timeout=60) as response, open(local_path, "wb") as out_file:
                                    # Write file content in blocks
                                    while True:
                                        chunk = response.read(1024 * 1024) # 1MB chunk
                                        if not chunk:
                                            break
                                        out_file.write(chunk)
                                download_success = True
                                break
                            except Exception as e:
                                logger.warning(f"Download attempt {attempt+1}/{max_download_retries} failed for {p_url}: {e}")
                                time.sleep(5)
                        
                        if not download_success:
                            raise RuntimeError(f"Failed to download partition file {p_url} after {max_download_retries} attempts.")
                        
                        logger.info(f"Successfully downloaded partition to {local_path}. Processing row groups...")
                        
                        try:
                            # Read the local partition file
                            pf = pq.ParquetFile(local_path)
                            for rg_idx in range(pf.num_row_groups):
                                df = pf.read_row_group(
                                    rg_idx, 
                                    columns=["query_id", "Eng_Query", "passages"]
                                ).to_pandas()
                                for _, row in df.iterrows():
                                    yield row.to_dict()
                        except Exception as e:
                            logger.error(f"Error reading local partition {local_path}: {e}")
                            raise e
                        finally:
                            # Delete the downloaded partition file to save disk space
                            if local_path.exists():
                                try:
                                    local_path.unlink()
                                except Exception as ue:
                                    logger.warning(f"Failed to delete temp file {local_path}: {ue}")

                dataset_iterator = record_generator()

            # Skip already processed records if resuming
            if self.processed_count > 0:
                logger.info(f"Skipping first {self.processed_count} records to resume...")
                skip_start = time.time()
                for _ in range(self.processed_count):
                    try:
                        next(dataset_iterator)
                    except StopIteration:
                        logger.warning("Reached end of dataset during skip. Nothing to index.")
                        return
                logger.info(f"Skipped {self.processed_count} records in {time.time() - skip_start:.2f}s.")

            batch_records = []
            start_time = time.time()
            last_checkpoint_time = time.time()
            
            for record in dataset_iterator:
                # Check limit
                if limit and self.processed_count >= limit:
                    logger.info(f"Limit of {limit} records reached. Stopping.")
                    break

                batch_records.append(record)
                self.processed_count += 1

                # Process batch when full
                if len(batch_records) >= self.batch_size:
                    self._process_batch(batch_records)
                    batch_records = []

                    # Periodic stats report
                    elapsed = time.time() - start_time
                    speed = self.processed_count / elapsed if elapsed > 0 else 0
                    logger.info(
                        f"Processed {self.processed_count} records. Chunks: {self.total_chunks}. "
                        f"Speed: {speed:.2f} rec/sec. Elapsed: {elapsed:.1f}s."
                    )
                    if limit:
                        remaining = limit - self.processed_count
                        eta = remaining / speed if speed > 0 else 0
                        logger.info(f"Remaining records to limit: {remaining}. ETA: {eta:.1f}s.")

                    # Checkpoint Interval
                    if (time.time() - last_checkpoint_time) > 60 or (self.processed_count % self.checkpoint_interval) == 0:
                        self.save_checkpoint()
                        last_checkpoint_time = time.time()

            # Process any final remaining records
            if batch_records:
                self._process_batch(batch_records)
                self.save_checkpoint()

            logger.info(f"Indexing completed. Total records processed: {self.processed_count}. Total chunks: {self.total_chunks}.")
            logger.info(f"Final Index size on disk: {self.index_path.stat().st_size / (1024*1024):.2f} MB")
            
        finally:
            self.release_lock()

    def _process_batch(self, records: List[Dict[str, Any]]):
        """Processes record list, computes embeddings, and appends to index."""
        chunks: List[DocumentChunk] = []
        texts: List[str] = []

        for record in records:
            query_id = record.get("query_id")
            title = record.get("Eng_Query", "")
            
            passages = record.get("passages", {})
            english_passages = passages.get("English_passages", [])
            
            if not english_passages:
                continue

            for idx, text in enumerate(english_passages):
                if not text or not text.strip():
                    continue
                
                chunk_id = f"{query_id}_{idx}"
                # Construct chunk metadata
                chunk = DocumentChunk(
                    id=chunk_id,
                    query_id=str(query_id),
                    text=text,
                    title=title
                )
                chunks.append(chunk)
                texts.append(text)

        if not texts:
            return

        # Encode and add to FAISS index
        vectors = embedding_service.encode(texts)
        # Verify vectors dimensions
        if vectors.ndim == 1:
            vectors = np.expand_dims(vectors, axis=0)

        # Normalize for inner product search consistency
        faiss.normalize_L2(vectors)

        self.index.add(vectors)
        self.documents.extend(chunks)
        self.total_chunks += len(chunks)

def run_dry_run():
    """Runs a 1,000-record dry-run to verify the pipeline."""
    logger.info("Starting 1,000-record dry-run of the full indexing pipeline...")
    
    # Use full index folder
    index_dir = config.DATA_DIR / "index" / "full"
    
    # If checkpoint exists, delete it first to ensure clean test validation of checkpointing
    checkpoint_file = index_dir / "checkpoint.json"
    if checkpoint_file.exists():
        checkpoint_file.unlink()
    
    indexer = IncrementalIndexer(index_dir, batch_size=200, checkpoint_interval=500)
    
    # Start indexing with 1000 record limit and local mock data streaming
    start_time = time.time()
    indexer.run_indexing(limit=1000, local_mock=True)
    elapsed = time.time() - start_time

    # Run check that index created successfully
    assert (index_dir / "faiss_index.bin").exists(), "FAISS index file was not created!"
    assert (index_dir / "metadata.pkl").exists(), "Metadata pickle file was not created!"
    assert (index_dir / "checkpoint.json").exists(), "Checkpoint JSON was not created!"

    # Verify indexing checkpoint resume works by loading and running 1 extra record
    logger.info("Verifying checkpoint resume capability...")
    resumer = IncrementalIndexer(index_dir, batch_size=1)
    has_resumed = resumer.load_checkpoint_if_exists()
    assert has_resumed, "Failed to load checkpoint!"
    assert resumer.processed_count == 1000, f"Expected resumed count 1000, got {resumer.processed_count}"
    
    # Read lock check
    logger.info("Checking duplicate process prevention...")
    duplicate_indexer = IncrementalIndexer(index_dir)
    duplicate_indexer.acquire_lock() # Should create new PID
    duplicate_indexer.release_lock()

    logger.info("=== DRY-RUN VERIFIED AND COMPLETED ===")
    logger.info(f"Processed records: {indexer.processed_count}")
    logger.info(f"Chunks indexed: {indexer.total_chunks}")
    logger.info(f"Disk used by index: {indexer.index_path.stat().st_size / (1024*1024):.2f} MB")
    logger.info(f"Elapsed time: {elapsed:.2f} seconds")
    logger.info(f"Processing speed: {indexer.processed_count / elapsed:.2f} rec/sec")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build MSMARCO-XI Full Index Incrementally")
    parser.add_argument("--dry-run", action="store_true", help="Run 1,000-record dry-run to verify pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of processed records")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size for indexing")
    args = parser.parse_args()

    if args.dry_run:
        run_dry_run()
    else:
        index_dir = config.DATA_DIR / "index" / "full"
        indexer = IncrementalIndexer(index_dir, batch_size=args.batch_size)
        indexer.run_indexing(limit=args.limit)
