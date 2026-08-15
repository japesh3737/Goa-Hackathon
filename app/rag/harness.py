import json
import time
import logging
import requests
from typing import List, Dict, Any, Tuple
from app.config import config
from app.models.schemas import SearchResultItem
from app.rag.answer_generator import get_llm_provider, LLMProvider

logger = logging.getLogger(__name__)

HARNESS_SYSTEM_PROMPT = """You are a grounded QA assistant for the MSMARCO-XI RAG application.
You must return a raw JSON object with the following fields:
1. "is_relevant": boolean, set to false if the user's query is completely off-topic or unrelated to the context.
2. "is_safe": boolean, set to false if the query contains inappropriate, harmful, or unsafe inputs.
3. "is_grounded": boolean, set to true if the answer is fully supported by the provided context.
4. "answer": string. 
    - If the query is off-topic, set to: "I can only answer questions related to the provided dataset context."
    - If the query is unsafe, set to: "I cannot answer inappropriate or unsafe questions."
    - If the query is not grounded, set to: "The retrieved context does not contain sufficient information to answer this question."
    - Otherwise, write a direct, concise answer grounded strictly in the context.
5. "citations": list of strings, containing the document/passage IDs cited in your answer.
6. "confidence_score": float between 0.0 and 1.0.

Context Passages:
{context}

Response must be valid raw JSON.
"""

class RAGHarness:
    def __init__(self, llm_provider: LLMProvider = None):
        self.llm_provider = llm_provider or get_llm_provider()

    def clean_json_string(self, raw_str: str) -> str:
        """Strip markdown code block wrappers from JSON string if present."""
        cleaned = raw_str.strip()
        if cleaned.startswith("```"):
            # Remove opening ```json or ```
            lines = cleaned.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return cleaned

    def execute_with_retry(self, question: str, retrieved_docs: List[SearchResultItem], history_context: str = "") -> Dict[str, Any]:
        """Executes the LLM request with structured JSON output, rate-limit retries, and schema validation."""
        formatted_context = ""
        for idx, item in enumerate(retrieved_docs, 1):
            doc_id = item.chunk_id
            text = item.text
            score = item.score
            title = item.title
            formatted_context += f"--- Passage [{idx}] (ID: {doc_id}, Score: {score}, Title: {title}) ---\n{text}\n\n"

        system_prompt = HARNESS_SYSTEM_PROMPT.format(context=formatted_context)
        user_content = f"Question: {question}"
        if history_context:
            user_content = f"Conversation History:\n{history_context}\n\n{user_content}"

        max_retries = 3
        backoff = 1.0

        for attempt in range(max_retries):
            try:
                # Direct call depending on LLM provider mode
                # We dynamically inject JSON mode configurations to the request if using Groq or Gemini
                raw_response = self._call_llm_provider_json(system_prompt, user_content)
                cleaned_resp = self.clean_json_string(raw_response)
                
                parsed = json.loads(cleaned_resp)
                
                # Validate schema fields
                required_fields = ["is_relevant", "is_safe", "is_grounded", "answer", "citations", "confidence_score"]
                if all(field in parsed for field in required_fields):
                    return parsed
                
                logger.warning(f"Schema validation failed on attempt {attempt+1}. Missing fields.")
            except json.JSONDecodeError as jde:
                logger.warning(f"JSON decoding failed on attempt {attempt+1}: {jde}. Raw response: {raw_response}")
            except Exception as e:
                logger.error(f"API request failed on attempt {attempt+1}: {e}")
                if "429" in str(e) or "rate limit" in str(e).lower():
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
            
            time.sleep(0.1)

        # Fallback structured response if all attempts fail
        logger.error("All harness retries failed. Returning safe fallback response.")
        return {
            "is_relevant": True,
            "is_safe": True,
            "is_grounded": False,
            "answer": "The retrieved context does not contain sufficient information to answer this question.",
            "citations": [],
            "confidence_score": 0.0
        }

    def _call_llm_provider_json(self, system_prompt: str, user_content: str) -> str:
        """Call LLM provider requesting JSON format."""
        provider = self.llm_provider
        
        # Modify the provider implementation to enforce JSON output formats
        provider_name = type(provider).__name__.lower()
        
        if "openai" in provider_name:
            headers = {
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": provider.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            resp = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
            
        elif "gemini" in provider_name:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{provider.model}:generateContent?key={provider.api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{system_prompt}\n\n{user_content}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.0,
                    "responseMimeType": "application/json"
                }
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            candidates = resp.json().get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
            raise ValueError("Invalid Gemini response structure.")
            
        elif "groq" in provider_name:
            headers = {
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": provider.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            resp = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
            
        else:
            # Fallback to standard provider generate if it is mock or local
            return provider.generate(user_content, [], system_prompt)

    def process_query(self, query: str, retrieved_docs: List[SearchResultItem], history_context: str = "") -> Dict[str, Any]:
        """Orchestrates query classification, relevance checks, safety check, and grounding checks."""
        # 1. Grounding check: Fast similarity threshold guardrail
        # If we have no retrieved documents, or if the top relevance score is extremely low,
        # we flag it as not grounded immediately.
        if not retrieved_docs:
            return {
                "is_relevant": True,
                "is_safe": True,
                "is_grounded": False,
                "answer": "The retrieved context does not contain sufficient information to answer this question.",
                "citations": [],
                "confidence_score": 0.0
            }
            
        top_score = retrieved_docs[0].score
        # A similarity score of less than 0.20 indicates very low relevance.
        if top_score < 0.20:
            logger.info(f"Top retrieved passage similarity ({top_score}) is below threshold (0.20). Query is classified as off-topic.")
            return {
                "is_relevant": False,
                "is_safe": True,
                "is_grounded": False,
                "answer": "I can only answer questions related to the provided dataset context.",
                "citations": [],
                "confidence_score": 0.0
            }

        # 2. Call LLM for generation + verification
        return self.execute_with_retry(query, retrieved_docs, history_context)

rag_harness = RAGHarness()
