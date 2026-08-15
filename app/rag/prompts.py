SYSTEM_PROMPT = """You are a grounded QA assistant for the MSMARCO-XI English RAG application.
Your task is to provide an accurate, clear, and direct answer to the user's question using ONLY the provided context passages.

Strict Rules:
1. Base your answer strictly on the evidence in the provided passages. Do not invent or assume facts.
2. If the provided context does not contain sufficient information to answer the question, state explicitly: "The retrieved context does not contain sufficient information to answer this question."
3. Cite source passage IDs (e.g. [Doc ID]) in your response where relevant.
4. Keep the answer concise, factual, and informative.
"""

def build_rag_prompt(question: str, context_passages: list) -> str:
    formatted_context = ""
    for idx, item in enumerate(context_passages, 1):
        if isinstance(item, dict):
            doc_id = item.get("chunk_id", f"doc_{idx}")
            text = item.get("text", "")
            score = item.get("score", 0.0)
            title = item.get("title", "")
        else:
            doc_id = getattr(item, "chunk_id", f"doc_{idx}")
            text = getattr(item, "text", "")
            score = getattr(item, "score", 0.0)
            title = getattr(item, "title", "")
        
        formatted_context += f"--- Passage [{idx}] (ID: {doc_id}, Score: {score}, Title: {title}) ---\n{text}\n\n"

    user_prompt = f"""Context Passages:
{formatted_context}

Question: {question}

Please answer the question grounded strictly in the context above:"""
    return user_prompt
