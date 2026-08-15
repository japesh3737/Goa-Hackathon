import re
import uuid
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from app.models.schemas import DocumentChunk
from app.config import config

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Normalize whitespace and strip unprintable characters."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def recursive_character_split(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """Splits text using recursive delimiters to keep sentences/paragraphs intact."""
    delimiters = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]
    
    def split_recurse(text_to_split: str, current_delimiters: List[str]) -> List[str]:
        if len(text_to_split) <= chunk_size:
            return [text_to_split]
        if not current_delimiters:
            return [text_to_split[i:i+chunk_size] for i in range(0, len(text_to_split), chunk_size - chunk_overlap)]
            
        delim = current_delimiters[0]
        next_delims = current_delimiters[1:]
        
        splits = text_to_split.split(delim)
        chunks = []
        current_chunk = ""
        
        for part in splits:
            part_str = part + (delim if part != splits[-1] else "")
            
            if len(part_str) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                chunks.extend(split_recurse(part_str, next_delims))
            elif len(current_chunk) + len(part_str) <= chunk_size:
                current_chunk += part_str
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = part_str
                
        if current_chunk:
            chunks.append(current_chunk)
            
        return [c.strip() for c in chunks if c.strip()]
        
    return split_recurse(text, delimiters)

def semantic_split(text: str, similarity_threshold_percentile: float = 35.0) -> List[str]:
    """Splits text into sentences, embeds them, and splits where similarity drops."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) <= 1:
        return [text]

    try:
        from app.retrieval.embeddings import embedding_service
        embeddings = embedding_service.encode(sentences, normalize_embeddings=True)
        
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = float(np.dot(embeddings[i], embeddings[i+1]))
            similarities.append(sim)
            
        if not similarities:
            return [text]
            
        threshold = np.percentile(similarities, similarity_threshold_percentile)
        
        chunks = []
        current_chunk_sentences = [sentences[0]]
        
        for i, sim in enumerate(similarities):
            if sim < threshold:
                chunks.append(" ".join(current_chunk_sentences))
                current_chunk_sentences = [sentences[i+1]]
            else:
                current_chunk_sentences.append(sentences[i+1])
                
        if current_chunk_sentences:
            chunks.append(" ".join(current_chunk_sentences))
            
        return chunks
    except Exception as e:
        logger.error(f"Semantic chunking failed: {e}. Falling back to recursive splitting.")
        return recursive_character_split(text)

def chunk_text(text: str, chunk_size: int = None, chunk_overlap: int = None) -> List[str]:
    """Fallback/default fixed-size word-based chunker."""
    chunk_size = chunk_size or config.CHUNK_SIZE
    chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP

    cleaned = clean_text(text)
    if not cleaned:
        return []

    words = cleaned.split(" ")
    if len(words) <= chunk_size / 5: # Short text
        return [cleaned]

    chunks = []
    word_chunk_size = max(10, chunk_size // 6)
    word_overlap = max(2, chunk_overlap // 6)

    step = max(1, word_chunk_size - word_overlap)
    for i in range(0, len(words), step):
        chunk_words = words[i:i + word_chunk_size]
        if chunk_words:
            chunks.append(" ".join(chunk_words))
        if i + word_chunk_size >= len(words):
            break

    return chunks or [cleaned]

def process_raw_record(record: Dict[str, Any]) -> List[DocumentChunk]:
    """Converts a raw dataset record into normalized DocumentChunk instances using the active CHUNK_STRATEGY."""
    query_id = str(record.get("query_id", record.get("id", uuid.uuid4().hex)))
    passages = record.get("passages", record.get("passage", record.get("text", "")))
    title = str(record.get("title", record.get("url", "")))
    strategy = config.CHUNK_STRATEGY

    chunks: List[DocumentChunk] = []

    def split_text_with_strategy(text_content: str) -> List[Dict[str, Any]]:
        cleaned = clean_text(text_content)
        if not cleaned:
            return []
        
        if strategy == "fixed":
            split_texts = chunk_text(cleaned)
            return [{"text": t, "metadata": {}} for t in split_texts]
        elif strategy == "semantic":
            split_texts = semantic_split(cleaned)
            return [{"text": t, "metadata": {}} for t in split_texts]
        elif strategy == "parent_child":
            parents = recursive_character_split(cleaned, chunk_size=600, chunk_overlap=100)
            child_chunks = []
            for p_idx, parent in enumerate(parents):
                children = recursive_character_split(parent, chunk_size=150, chunk_overlap=30)
                for c_idx, child in enumerate(children):
                    child_chunks.append({
                        "text": child,
                        "metadata": {
                            "parent_text": parent,
                            "parent_index": p_idx,
                            "child_index": c_idx
                        }
                    })
            return child_chunks
        else: # default: recursive
            split_texts = recursive_character_split(cleaned)
            return [{"text": t, "metadata": {}} for t in split_texts]

    if isinstance(passages, list):
        for idx, passage in enumerate(passages):
            if isinstance(passage, dict):
                p_text = passage.get("passage_text", passage.get("text", ""))
                is_rel = passage.get("is_selected", passage.get("is_relevant", True))
                p_title = passage.get("title", title)
            else:
                p_text = str(passage)
                is_rel = True
                p_title = title

            processed = split_text_with_strategy(p_text)
            for chunk_idx, item in enumerate(processed):
                meta = {"passage_index": idx, "chunk_index": chunk_idx}
                meta.update(item["metadata"])
                chunks.append(DocumentChunk(
                    id=f"{query_id}_p{idx}_c{chunk_idx}",
                    query_id=query_id,
                    text=item["text"],
                    title=p_title,
                    source="MSMARCO-XI",
                    is_relevant=bool(is_rel),
                    metadata=meta
                ))
    elif isinstance(passages, str):
        processed = split_text_with_strategy(passages)
        for chunk_idx, item in enumerate(processed):
            meta = {"chunk_index": chunk_idx}
            meta.update(item["metadata"])
            chunks.append(DocumentChunk(
                id=f"{query_id}_c{chunk_idx}",
                query_id=query_id,
                text=item["text"],
                title=title,
                source="MSMARCO-XI",
                is_relevant=True,
                metadata=meta
            ))

    return chunks
