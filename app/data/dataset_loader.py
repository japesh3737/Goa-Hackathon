import os
import json
import logging
import pandas as pd
from typing import List, Dict, Any
from app.config import config
from app.data.preprocessing import process_raw_record, clean_text
from app.models.schemas import DocumentChunk

logger = logging.getLogger(__name__)

class MSMARCODatasetLoader:
    def __init__(self, dataset_name: str = None, sample_size: int = None):
        self.dataset_name = dataset_name or config.DATASET_NAME
        self.sample_size = sample_size or config.SAMPLE_SIZE

    def create_sample_file(self, limit: int = None, output_path: str = None) -> str:
        limit = limit or self.sample_size
        output_path = output_path or str(config.PROCESSED_DATA_PATH)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        logger.info(f"Creating sample dataset of size {limit}...")
        extracted_chunks: List[Dict[str, Any]] = self._generate_fallback_sample(limit)

        df = pd.DataFrame(extracted_chunks)
        df.to_parquet(output_path, index=False)
        logger.info(f"Successfully saved {len(df)} processed chunks to {output_path}")
        return output_path

    def _load_via_parquet_direct(self, limit: int) -> List[Dict[str, Any]]:
        extracted_chunks = []
        try:
            import urllib.request
            url = f"https://huggingface.co/api/datasets/{self.dataset_name}/parquet"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            
            parquet_urls = data.get("default", {}).get("train", [])
            if parquet_urls:
                df = pd.read_parquet(parquet_urls[0])
                count = 0
                for _, row in df.iterrows():
                    if count >= limit:
                        break
                    record = row.to_dict()
                    chunks = process_raw_record(record)
                    for chunk in chunks:
                        extracted_chunks.append(chunk.model_dump())
                    count += 1
        except Exception as ex:
            logger.error(f"Parquet direct fetch error: {ex}")
        return extracted_chunks

    def _generate_fallback_sample(self, limit: int) -> List[Dict[str, Any]]:
        """Generates representative English MSMARCO sample documents for baseline dev/test."""
        sample_topics = [
            ("Photosynthesis", "Photosynthesis is a process used by plants and other organisms to convert light energy into chemical energy that, through cellular respiration, can later be released to fuel the organisms' activities. This chemical energy is stored in carbohydrate molecules, such as sugars."),
            ("Python Programming Language", "Python is a high-level, general-purpose programming language. Its design philosophy emphasizes code readability with the use of significant indentation. Python is dynamically typed and garbage-collected. It supports multiple programming paradigms, including structured, object-oriented and functional programming."),
            ("MS MARCO Dataset", "MS MARCO (Microsoft Machine Reading Comprehension) is a collection of datasets focused on deep learning in search and reading comprehension. The dataset consists of 1,010,916 real Bing search queries, 182,669 rewritten queries, and 8,841,823 passages extracted from web pages."),
            ("Artificial Intelligence", "Artificial intelligence (AI) is the intelligence of machines or software, as opposed to the intelligence of living beings, primarily of humans. It is a field of study in computer science that develops and studies intelligent machines."),
            ("FastAPI Framework", "FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.8+ based on standard Python type hints. It is built on top of Starlette for web parts and Pydantic for data parts.")
        ]
        
        chunks = []
        for idx in range(min(limit, 500)):
            topic, desc = sample_topics[idx % len(sample_topics)]
            chunk = DocumentChunk(
                id=f"doc_{idx}",
                query_id=f"q_{idx // len(sample_topics)}",
                text=f"{topic} Overview: {desc} (Sample document #{idx} for MSMARCO-XI evaluation)",
                title=topic,
                source="MSMARCO-XI English Sample",
                is_relevant=True,
                metadata={"sample_id": idx}
            )
            chunks.append(chunk.model_dump())
        return chunks

    def load_processed_sample(self, path: str = None) -> List[DocumentChunk]:
        path = path or str(config.PROCESSED_DATA_PATH)
        if not os.path.exists(path):
            self.create_sample_file(output_path=path)
        df = pd.read_parquet(path)
        chunks = []
        for _, row in df.iterrows():
            d = row.to_dict()
            if isinstance(d.get("metadata"), str):
                try:
                    d["metadata"] = json.loads(d["metadata"])
                except Exception:
                    d["metadata"] = {}
            chunks.append(DocumentChunk(**d))
        return chunks
