import re
import uuid
import logging
from typing import List, Dict, Any, Optional
from app.models.schemas import DocumentChunk
from app.config import config

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Normalize whitespace, remove extraneous characters, and preserve punctuation."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def split_into_sentences(text: str) -> List[str]:
    """Splits text cleanly along sentence boundaries without breaking abbreviations."""
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'\(\[])', text)
    return [s.strip() for s in sentences if s.strip()]

def sentence_window_chunk(text: str, target_chunk_size: int = 750, sentence_overlap: int = 2) -> List[str]:
    """
    Intelligent sentence-window chunker:
    Groups complete sentences until reaching target_chunk_size, then overlaps the last N sentences.
    Never cuts sentences or words in half.
    """
    cleaned = clean_text(text)
    if not cleaned:
        return []

    if len(cleaned) <= target_chunk_size:
        return [cleaned]

    sentences = split_into_sentences(cleaned)
    if len(sentences) <= 1:
        return recursive_character_split(cleaned, chunk_size=target_chunk_size, chunk_overlap=80)

    chunks = []
    current_sentences = []
    current_length = 0

    for sentence in sentences:
        sentence_len = len(sentence) + 1
        if current_sentences and (current_length + sentence_len > target_chunk_size):
            chunks.append(" ".join(current_sentences).strip())
            overlap_sentences = current_sentences[-sentence_overlap:] if sentence_overlap > 0 else []
            current_sentences = list(overlap_sentences)
            current_length = sum(len(s) + 1 for s in current_sentences)

        current_sentences.append(sentence)
        current_length += sentence_len

    if current_sentences:
        chunks.append(" ".join(current_sentences).strip())

    return [c for c in chunks if len(c) > 20]

def recursive_character_split(text: str, chunk_size: int = 750, chunk_overlap: int = 80) -> List[str]:
    """Splits text using hierarchical delimiters to keep paragraphs/sentences intact."""
    delimiters = ["\n\n", "\n", ". ", "? ", "! ", "; ", " ", ""]
    
    def split_recurse(text_to_split: str, current_delimiters: List[str]) -> List[str]:
        if len(text_to_split) <= chunk_size:
            return [text_to_split]
        if not current_delimiters:
            return [text_to_split[i:i+chunk_size] for i in range(0, len(text_to_split), max(1, chunk_size - chunk_overlap))]
            
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

# Backward-compatible aliases
def chunk_text(text: str, chunk_size: int = None, chunk_overlap: int = None) -> List[str]:
    size = chunk_size or config.CHUNK_SIZE
    return sentence_window_chunk(text, target_chunk_size=size, sentence_overlap=2)

def semantic_split(text: str, similarity_threshold_percentile: float = 35.0) -> List[str]:
    return sentence_window_chunk(text, target_chunk_size=500, sentence_overlap=1)

def process_raw_record(record: Dict[str, Any], chunk_size: int = 750) -> List[DocumentChunk]:
    """
    Converts raw dataset records into clean, contextual DocumentChunk instances.
    Respects CHUNK_STRATEGY (sentence, recursive, parent_child).
    """
    query_id = str(record.get("query_id", record.get("id", uuid.uuid4().hex)))
    passages = record.get("passages", record.get("passage", record.get("text", "")))
    title = clean_text(str(record.get("title", record.get("url", ""))))
    strategy = config.CHUNK_STRATEGY
    
    chunks: List[DocumentChunk] = []

    def split_text_with_strategy(text_content: str) -> List[Dict[str, Any]]:
        cleaned = clean_text(text_content)
        if not cleaned:
            return []
        
        if strategy == "parent_child":
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
        else:
            split_texts = sentence_window_chunk(cleaned, target_chunk_size=chunk_size, sentence_overlap=1)
            return [{"text": t, "metadata": {}} for t in split_texts]

    if isinstance(passages, list):
        for idx, passage in enumerate(passages):
            if isinstance(passage, dict):
                p_text = clean_text(passage.get("passage_text", passage.get("text", "")))
                p_title = clean_text(passage.get("title", title))
                is_rel = passage.get("is_selected", passage.get("is_relevant", True))
            else:
                p_text = clean_text(str(passage))
                p_title = title
                is_rel = True

            if not p_text:
                continue

            processed = split_text_with_strategy(p_text)
            for chunk_idx, item in enumerate(processed):
                meta = {"passage_index": idx, "chunk_index": chunk_idx, "title": p_title}
                meta.update(item["metadata"])
                chunks.append(DocumentChunk(
                    id=f"{query_id}_p{idx}_c{chunk_idx}",
                    query_id=query_id,
                    text=item["text"],
                    title=p_title or f"Passage #{idx+1}",
                    source="MSMARCO-XI",
                    is_relevant=bool(is_rel),
                    metadata=meta
                ))
    elif isinstance(passages, str) and passages.strip():
        cleaned_passage = clean_text(passages)
        processed = split_text_with_strategy(cleaned_passage)
        for chunk_idx, item in enumerate(processed):
            meta = {"chunk_index": chunk_idx, "title": title}
            meta.update(item["metadata"])
            chunks.append(DocumentChunk(
                id=f"{query_id}_c{chunk_idx}",
                query_id=query_id,
                text=item["text"],
                title=title or "Document",
                source="MSMARCO-XI",
                is_relevant=True,
                metadata=meta
            ))

    return chunks
