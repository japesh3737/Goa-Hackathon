import math
import re
import numpy as np
from app.data.dataset_loader import CURATED_KNOWLEDGE_BASE
from app.retrieval.embeddings import embedding_service

def tokenize(text):
    return re.findall(r'\w+', text.lower())

class BM25Retriever:
    def __init__(self, corpus):
        self.corpus = corpus
        self.doc_len = [len(tokenize(d)) for d in corpus]
        self.avg_doc_len = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 1.0
        self.doc_freqs = []
        self.df = {}
        for d in corpus:
            freqs = {}
            for w in tokenize(d):
                freqs[w] = freqs.get(w, 0) + 1
            self.doc_freqs.append(freqs)
            for w in freqs:
                self.df[w] = self.df.get(w, 0) + 1

    def get_scores(self, query):
        q_tokens = tokenize(query)
        scores = []
        k1, b = 1.5, 0.75
        N = len(self.corpus)
        for idx, freqs in enumerate(self.doc_freqs):
            score = 0.0
            for w in q_tokens:
                if w in freqs:
                    tf = freqs[w]
                    df = self.df.get(w, 0)
                    idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
                    doc_len = self.doc_len[idx]
                    denom = tf + k1 * (1.0 - b + b * (doc_len / self.avg_doc_len))
                    score += idf * (tf * (k1 + 1.0)) / denom
            scores.append(score)
        return np.array(scores)

corpus_texts = [f"{item['title']} {item['text']}" for item in CURATED_KNOWLEDGE_BASE]
bm25 = BM25Retriever(corpus_texts)

queries = [
    "What are the famous dishes in Goan cuisine?",
    "What is photosynthesis?",
    "Tell me about Goa history and Portuguese rule.",
    "What is FAISS vector search?",
    "What is Python programming language?"
]

for query in queries:
    q_vec = embedding_service.encode(query, normalize_embeddings=True).flatten()
    bm_scores = bm25.get_scores(query)
    max_bm = max(bm_scores) if max(bm_scores) > 0 else 1.0
    bm_norm = bm_scores / max_bm

    results = []
    for idx, item in enumerate(CURATED_KNOWLEDGE_BASE):
        title = item['title']
        embed_str = f"{title}: {item['text']}"
        d_vec = embedding_service.encode(embed_str, normalize_embeddings=True).flatten()
        dense_sim = float(np.dot(q_vec, d_vec))
        
        # Hybrid Score: 60% Keyword Token Match + 40% Dense Vector Embedding
        hybrid = 0.60 * bm_norm[idx] + 0.40 * dense_sim
        results.append((hybrid, dense_sim, bm_norm[idx], title))

    results.sort(key=lambda x: x[0], reverse=True)
    print(f"\nQuery: '{query}'")
    for h, d, b, t in results[:3]:
        print(f"  -> Rank 1: Hybrid={h:.3f} (BM25={b:.2f}, Dense={d:.3f}) | {t}")
