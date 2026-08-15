import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retrieval.retriever import retriever_service
from app.rag.pipeline import rag_pipeline_service

EVAL_BENCHMARK = [
    {
        "query": "What is photosynthesis?",
        "expected_keywords": ["photosynthesis", "plant", "light", "energy"]
    },
    {
        "query": "What is Python programming language?",
        "expected_keywords": ["python", "programming", "language", "dynamic"]
    },
    {
        "query": "What is MS MARCO dataset?",
        "expected_keywords": ["ms marco", "dataset", "bing", "passage", "queries"]
    },
    {
        "query": "What is artificial intelligence?",
        "expected_keywords": ["artificial intelligence", "ai", "machine", "software"]
    },
    {
        "query": "What is FastAPI?",
        "expected_keywords": ["fastapi", "python", "framework", "api"]
    }
]

def run_evaluation(top_k: int = 5):
    print("=== Running MSMARCO-XI RAG Agent Evaluation ===")
    
    # Check if API keys are present; if not, use Mock LLM for the benchmark evaluation run
    from app.config import config
    from app.rag.answer_generator import MockGroundedLLMProvider
    if not config.GEMINI_API_KEY and not config.LLM_API_KEY:
        print("[NOTE] API keys unconfigured. Running evaluation using MockGroundedLLMProvider fallback.")
        rag_pipeline_service.llm_provider = MockGroundedLLMProvider()

    results = []
    total_mrr = 0.0
    total_recall = 0.0
    retrieval_latencies = []
    generation_latencies = []

    for item in EVAL_BENCHMARK:
        query = item["query"]
        expected = item["expected_keywords"]

        # Measure Retrieval
        start_r = time.time()
        retrieved = retriever_service.retrieve(query, top_k=top_k)
        ret_time = time.time() - start_r
        retrieval_latencies.append(ret_time)

        # Check MRR & Recall
        found_rank = None
        hits = 0
        for idx, doc in enumerate(retrieved, 1):
            text_lower = doc.text.lower()
            if any(kw in text_lower for kw in expected):
                if found_rank is None:
                    found_rank = idx
                hits += 1

        reciprocal_rank = 1.0 / found_rank if found_rank else 0.0
        recall = 1.0 if hits > 0 else 0.0

        total_mrr += reciprocal_rank
        total_recall += recall

        # Measure RAG pipeline
        start_g = time.time()
        rag_resp = rag_pipeline_service.answer_question(query, top_k=top_k)
        gen_time = time.time() - start_g
        generation_latencies.append(gen_time)

        results.append({
            "query": query,
            "top_k": top_k,
            "found_rank": found_rank,
            "mrr": round(reciprocal_rank, 4),
            "recall": recall,
            "retrieved_count": len(retrieved),
            "answer_preview": rag_resp.answer[:120] + "...",
            "retrieval_latency_sec": round(ret_time, 4),
            "generation_latency_sec": round(gen_time, 4)
        })

    num_queries = len(EVAL_BENCHMARK)
    mean_mrr = round(total_mrr / num_queries, 4)
    mean_recall = round(total_recall / num_queries, 4)
    avg_ret_lat = round(sum(retrieval_latencies) / num_queries, 4)
    avg_gen_lat = round(sum(generation_latencies) / num_queries, 4)

    summary = {
        "benchmark_queries": num_queries,
        "mean_reciprocal_rank_mrr": mean_mrr,
        "mean_recall_at_k": mean_recall,
        "avg_retrieval_latency_sec": avg_ret_lat,
        "avg_generation_latency_sec": avg_gen_lat,
        "detailed_results": results
    }

    output_path = Path("data/evaluation_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n--- EVALUATION SUMMARY ---")
    print(f"Mean Reciprocal Rank (MRR@{top_k}): {mean_mrr}")
    print(f"Mean Recall@{top_k}: {mean_recall}")
    print(f"Avg Retrieval Latency: {avg_ret_lat}s")
    print(f"Avg Generation Latency: {avg_gen_lat}s")
    print(f"Report saved to {output_path}")

if __name__ == "__main__":
    run_evaluation()
