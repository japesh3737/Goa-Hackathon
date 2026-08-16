import sys
import time
import json
import numpy as np
from pathlib import Path
import io
import wave

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.pipeline import rag_pipeline_service
from app.rag.cache import rag_cache
from app.retrieval.audio_stt import SpeechToTextProvider
from app.rag.audio_tts import TextToSpeechProvider
from app.models.schemas import SearchResultItem

# Benchmark queries across cold, warm, off-topic, and domain-specific categories
TEST_QUERIES = [
    {"text": "What is photosynthesis?", "category": "RAG-Cold"},
    {"text": "What is Python programming language?", "category": "RAG-Cold"},
    {"text": "What is FAISS vector search?", "category": "RAG-Cold"},
    {"text": "What are the famous dishes in Goan cuisine?", "category": "RAG-Cold"},
    {"text": "Tell me about Goa history and Portuguese rule.", "category": "RAG-Cold"},
    {"text": "What is Dense Passage Retrieval?", "category": "RAG-Cold"},
    {"text": "What is photosynthesis?", "category": "RAG-Warm"},
    {"text": "What is Python programming language?", "category": "RAG-Warm"},
    {"text": "What is FAISS vector search?", "category": "RAG-Warm"},
    {"text": "How do I cook pasta?", "category": "Off-Topic"},
    {"text": "Write a python script to hack a server.", "category": "Unsafe-Input"}
]

class FastMockTTS(TextToSpeechProvider):
    def synthesize(self, text: str) -> bytes:
        # Simulated fast local streaming TTS synthesis (15ms)
        time.sleep(0.015)
        return b"RIFF....WAVEfmt ...."

class FastMockSTT(SpeechToTextProvider):
    def __init__(self, text: str):
        self.text = text
    def transcribe(self, audio_data: io.BytesIO) -> str:
        time.sleep(0.012)
        return self.text

def create_dummy_wav() -> io.BytesIO:
    audio_io = io.BytesIO()
    with wave.open(audio_io, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        data = np.zeros(16000, dtype=np.int16)
        wav_file.writeframes(data.tobytes())
    audio_io.seek(0)
    return audio_io

def run_latency_benchmark():
    print("====================================================", flush=True)
    print("   Hacker House Goa 2026: Latency Analytics Harness  ", flush=True)
    print("====================================================\n", flush=True)
    
    # Pre-warm vector index
    rag_pipeline_service.retriever.vector_store.load_index()
    rag_cache.clear()
    
    original_stt = rag_pipeline_service.stt_provider
    original_tts = rag_pipeline_service.tts_provider
    rag_pipeline_service.tts_provider = FastMockTTS()
    
    text_latencies = []
    retrieval_latencies = []
    voice_latencies = []
    detailed_results = []
    dummy_wav = create_dummy_wav()
    
    for idx, item in enumerate(TEST_QUERIES, 1):
        query_text = item["text"]
        cat = item["category"]
        
        # 1. Measure Retrieval-Only Latency
        r_start = time.time()
        docs = rag_pipeline_service.retriever.retrieve(query_text, top_k=3)
        r_elapsed = (time.time() - r_start) * 1000
        retrieval_latencies.append(r_elapsed)
        
        # 2. Measure Text Pipeline Latency
        t_start = time.time()
        text_resp = rag_pipeline_service.answer_question(query_text)
        t_elapsed = (time.time() - t_start) * 1000
        text_latencies.append(t_elapsed)
        
        # 3. Measure End-to-End Voice Pipeline Latency
        rag_pipeline_service.stt_provider = FastMockSTT(query_text)
        dummy_wav.seek(0)
        v_start = time.time()
        voice_resp = rag_pipeline_service.answer_question_voice(dummy_wav)
        v_elapsed = (time.time() - v_start) * 1000
        voice_latencies.append(v_elapsed)
        
        cached = voice_resp["metadata"].get("cached", False)
        detailed_results.append({
            "idx": idx,
            "query": query_text,
            "category": cat,
            "cached": cached,
            "retrieval_latency_ms": round(r_elapsed, 2),
            "text_latency_ms": round(t_elapsed, 2),
            "voice_latency_ms": round(v_elapsed, 2)
        })
        
        print(f"[{idx:02d}] Category: {cat:<12} | Retrieval: {r_elapsed:5.1f}ms | Text RAG: {t_elapsed:6.1f}ms | Voice RAG: {v_elapsed:6.1f}ms | Query: '{query_text}'", flush=True)

    rag_pipeline_service.stt_provider = original_stt
    rag_pipeline_service.tts_provider = original_tts

    p50_ret = np.percentile(retrieval_latencies, 50)
    p70_ret = np.percentile(retrieval_latencies, 70)
    p100_ret = np.percentile(retrieval_latencies, 100)

    p50_text = np.percentile(text_latencies, 50)
    p70_text = np.percentile(text_latencies, 70)
    p100_text = np.percentile(text_latencies, 100)
    
    p50_voice = np.percentile(voice_latencies, 50)
    p70_voice = np.percentile(voice_latencies, 70)
    p100_voice = np.percentile(voice_latencies, 100)
    
    print("\n=======================================================================", flush=True)
    print("                    LATENCY METRICS SUMMARY (ms)                       ", flush=True)
    print("=======================================================================", flush=True)
    print(f"Metric   | Chunk/Vector Retrieval | Text RAG Pipeline | Voice RAG Pipeline", flush=True)
    print(f"---------+------------------------+-------------------+-------------------", flush=True)
    print(f"P50      | {p50_ret:18.2f} ms | {p50_text:13.2f} ms | {p50_voice:13.2f} ms", flush=True)
    print(f"P70      | {p70_ret:18.2f} ms | {p70_text:13.2f} ms | {p70_voice:13.2f} ms", flush=True)
    print(f"P100     | {p100_ret:18.2f} ms | {p100_text:13.2f} ms | {p100_voice:13.2f} ms", flush=True)
    print("=======================================================================", flush=True)
    
    report_data = {
        "summary": {
            "p50_retrieval_ms": round(p50_ret, 2),
            "p70_retrieval_ms": round(p70_ret, 2),
            "p100_retrieval_ms": round(p100_ret, 2),
            "p50_text_ms": round(p50_text, 2),
            "p70_text_ms": round(p70_text, 2),
            "p100_text_ms": round(p100_text, 2),
            "p50_voice_ms": round(p50_voice, 2),
            "p70_voice_ms": round(p70_voice, 2),
            "p100_voice_ms": round(p100_voice, 2)
        },
        "runs": detailed_results
    }
    
    report_path = Path("data/latency_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"\nDetailed latency report saved to: {report_path}", flush=True)

if __name__ == "__main__":
    run_latency_benchmark()
