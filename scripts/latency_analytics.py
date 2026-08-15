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

# Clear cache to get authentic cold start readings
rag_cache.clear()

TEST_QUERIES = [
    # RAG Cold
    {"text": "What is photosynthesis?", "category": "RAG-Cold"},
    {"text": "What is Python programming language?", "category": "RAG-Cold"},
    {"text": "What is MS MARCO dataset?", "category": "RAG-Cold"},
    {"text": "What is artificial intelligence?", "category": "RAG-Cold"},
    {"text": "What is FastAPI?", "category": "RAG-Cold"},
    
    # RAG Warm (Cached hits)
    {"text": "What is photosynthesis?", "category": "RAG-Warm"},
    {"text": "What is Python programming language?", "category": "RAG-Warm"},
    {"text": "What is MS MARCO dataset?", "category": "RAG-Warm"},
    
    # Off-Topic / Guardrails (Fast rejection)
    {"text": "How do I cook pasta?", "category": "Off-Topic"},
    {"text": "Write a python function to sort a list.", "category": "Off-Topic"},
    {"text": "Tell me a joke.", "category": "Off-Topic"},
    
    # Context-aware Follow-ups
    {"text": "What is artificial intelligence?", "category": "RAG-Cold"},
    {"text": "Is it dynamically typed?", "category": "RAG-Cold"}
]

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
    print("====================================================")
    print("   Hacker House Goa 2026: Latency Analytics Harness  ")
    print("====================================================\n")
    
    print("Loading vector database and warming up embeddings...")
    rag_pipeline_service.retriever.vector_store.load_index()
    print("Warm-up complete!\n")

    original_stt = rag_pipeline_service.stt_provider
    
    class BenchmarkSTT(SpeechToTextProvider):
        def __init__(self, target_text: str):
            self.target_text = target_text
        def transcribe(self, audio_data: io.BytesIO) -> str:
            # Simulate local/streaming STT response network overhead
            time.sleep(0.01)
            return self.target_text

    text_latencies = []
    voice_latencies = []
    
    detailed_results = []
    
    dummy_wav = create_dummy_wav()
    
    for idx, item in enumerate(TEST_QUERIES, 1):
        query_text = item["text"]
        cat = item["category"]
        
        # 1. Benchmark Text RAG Pipeline
        t_start = time.time()
        text_resp = rag_pipeline_service.answer_question(query_text)
        t_elapsed = (time.time() - t_start) * 1000 # in ms
        text_latencies.append(t_elapsed)
        
        # 2. Benchmark Voice RAG Pipeline
        rag_pipeline_service.stt_provider = BenchmarkSTT(query_text)
        dummy_wav.seek(0)
        
        v_start = time.time()
        voice_resp = rag_pipeline_service.answer_question_voice(dummy_wav)
        v_elapsed = (time.time() - v_start) * 1000 # in ms
        voice_latencies.append(v_elapsed)
        
        cached = voice_resp["metadata"].get("cached", False)
        stt_time = voice_resp["metadata"].get("stt_time_sec", 0.0) * 1000
        ret_time = voice_resp["metadata"].get("retrieval_time_sec", 0.0) * 1000
        gen_time = voice_resp["metadata"].get("generation_time_sec", 0.0) * 1000
        tts_time = voice_resp["metadata"].get("tts_time_sec", 0.0) * 1000
        
        detailed_results.append({
            "idx": idx,
            "query": query_text,
            "category": cat,
            "cached": cached,
            "text_latency_ms": t_elapsed,
            "voice_latency_ms": v_elapsed,
            "stt_ms": stt_time,
            "retrieval_ms": ret_time,
            "generation_ms": gen_time,
            "tts_ms": tts_time
        })
        
        print(f"[{idx:02d}] Category: {cat:<10} | Cached: {str(cached):<5} | Text: {t_elapsed:6.1f}ms | Voice: {v_elapsed:6.1f}ms | Query: '{query_text}'")

    rag_pipeline_service.stt_provider = original_stt

    p50_text = np.percentile(text_latencies, 50)
    p70_text = np.percentile(text_latencies, 70)
    p100_text = np.percentile(text_latencies, 100)
    
    p50_voice = np.percentile(voice_latencies, 50)
    p70_voice = np.percentile(voice_latencies, 70)
    p100_voice = np.percentile(voice_latencies, 100)
    
    print("\n====================================================")
    print("            LATENCY METRICS SUMMARY (ms)            ")
    print("====================================================")
    print(f"Metric   | Text RAG Pipeline | Voice RAG Pipeline (incl. Mock STT)")
    print(f"---------+-------------------+------------------------------------")
    print(f"P50      | {p50_text:13.2f} ms | {p50_voice:13.2f} ms")
    print(f"P70      | {p70_text:13.2f} ms | {p70_voice:13.2f} ms")
    print(f"P100     | {p100_text:13.2f} ms | {p100_voice:13.2f} ms")
    print("====================================================")
    
    report_data = {
        "summary": {
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
    print(f"Detailed latency report saved to: {report_path}")

if __name__ == "__main__":
    run_latency_benchmark()
