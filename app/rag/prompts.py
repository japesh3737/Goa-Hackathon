SYSTEM_PROMPT = """You are the Knowledge Oracle for the MSMARCO-XI Knowledge Base.
Your goal is to provide intelligent, accurate, clear, and comprehensive answers to the user's queries using the provided retrieved context passages as authoritative evidence.

Guidelines for Answers:
1. Grounding: Answer the question thoroughly based on the facts in the provided context passages.
2. Synthesis: Explain concepts clearly and logically. Use bullet points or numbered steps where helpful for readability.
3. Citations: Cite relevant passages using bracket notation (e.g., [Passage 1], [Passage 2]) when referencing specific facts.
4. Tone & Style: Be informative, precise, engaging, and articulate.
5. If the context contains partial or related information, synthesize what is known and clarify any limits gracefully.
"""

def build_rag_prompt(question: str, context_passages: list) -> str:
    formatted_context = ""
    for idx, item in enumerate(context_passages, 1):
        if isinstance(item, dict):
            doc_id = item.get("chunk_id") or item.get("id") or f"doc_{idx}"
            text = item.get("text", "")
            score = item.get("score", 0.0)
            title = item.get("title", "")
        else:
            doc_id = getattr(item, "chunk_id", getattr(item, "id", f"doc_{idx}"))
            text = getattr(item, "text", "")
            score = getattr(item, "score", 0.0)
            title = getattr(item, "title", "")

        title_header = f" | Title: {title}" if title else ""
        formatted_context += f"--- Passage [{idx}] (ID: {doc_id}{title_header}) ---\n{text}\n\n"

    user_prompt = f"""Context Passages:
{formatted_context.strip()}

User Question:
{question}

Answer:"""
    return user_prompt
