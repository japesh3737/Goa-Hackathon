import os
import json
import logging
import requests
from typing import List, Dict, Any
from app.config import config
from app.rag.prompts import SYSTEM_PROMPT, build_rag_prompt
from app.models.schemas import SearchResultItem

logger = logging.getLogger(__name__)

class LLMProvider:
    def generate(self, question: str, retrieved_docs: List[SearchResultItem], history_context: str = "") -> str:
        raise NotImplementedError

class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider using direct REST endpoint for maximum robustness."""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.GEMINI_API_KEY or config.LLM_API_KEY
        self.model = model or config.LLM_MODEL or "gemini-1.5-flash"

    def generate(self, question: str, retrieved_docs: List[SearchResultItem], history_context: str = "") -> str:
        if not self.api_key:
            logger.error("Gemini API key (GEMINI_API_KEY) is not configured in .env.")
            raise ValueError(
                "Gemini API key is missing. Please configure GEMINI_API_KEY in your .env file."
            )

        user_content = build_rag_prompt(question, retrieved_docs)
        if history_context:
            user_content = f"{history_context}\n{user_content}"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {
            "Content-Type": "application/json"
        }
        
        # Format payload according to Google Gemini API standards
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{SYSTEM_PROMPT}\n\n{user_content}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2
            }
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            # Extract content text from response structure
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
            raise ValueError("Unexpected response structure from Gemini API.")
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise RuntimeError(f"Gemini API call failed: {str(e)}")

class OpenAIProvider(LLMProvider):
    """OpenAI GPT LLM provider."""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.LLM_API_KEY
        self.model = model or config.LLM_MODEL or "gpt-3.5-turbo"

    def generate(self, question: str, retrieved_docs: List[SearchResultItem], history_context: str = "") -> str:
        if not self.api_key:
            logger.error("OpenAI API key (LLM_API_KEY) is not configured in .env.")
            raise ValueError(
                "OpenAI API key is missing. Please configure LLM_API_KEY in your .env file."
            )

        user_content = build_rag_prompt(question, retrieved_docs)
        if history_context:
            user_content = f"{history_context}\n{user_content}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.2
        }

        try:
            resp = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise RuntimeError(f"OpenAI API call failed: {str(e)}")

class OllamaProvider(LLMProvider):
    """Local Ollama LLM provider."""
    def __init__(self, model: str = None, host: str = "http://localhost:11434"):
        self.model = model or config.LLM_MODEL or "llama2"
        self.host = host

    def generate(self, question: str, retrieved_docs: List[SearchResultItem], history_context: str = "") -> str:
        user_content = build_rag_prompt(question, retrieved_docs)
        if history_context:
            user_content = f"{history_context}\n{user_content}"

        try:
            resp = requests.post(
                f"{self.host}/api/generate",
                json={"model": self.model, "prompt": f"{SYSTEM_PROMPT}\n\n{user_content}", "stream": False},
                timeout=30
            )
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
        except Exception as e:
            logger.error(f"Ollama API call failed: {e}")
            raise RuntimeError(f"Ollama service unavailable: {str(e)}")

class GroqProvider(LLMProvider):
    """Groq LLM provider using direct REST endpoint (OpenAI compatible)."""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.GROQ_API_KEY
        self.model = model or config.LLM_MODEL or "llama-3.1-8b-instant"

    def generate(self, question: str, retrieved_docs: List[SearchResultItem], history_context: str = "") -> str:
        if not self.api_key:
            logger.error("Groq API key (GROQ_API_KEY) is not configured in .env.")
            raise ValueError(
                "Groq API key is missing. Please configure GROQ_API_KEY in your .env file."
            )

        user_content = build_rag_prompt(question, retrieved_docs)
        if history_context:
            user_content = f"{history_context}\n{user_content}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.2
        }

        try:
            resp = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            raise RuntimeError(f"Groq API call failed: {str(e)}")

class MockGroundedLLMProvider(LLMProvider):
    """Fallback mock grounded synthesizer for unit testing purposes."""
    def generate(self, question: str, retrieved_docs: List[SearchResultItem], history_context: str = "") -> str:
        if not retrieved_docs:
            return "The retrieved context does not contain sufficient information to answer this question."

        top_doc = retrieved_docs[0]
        doc_summary = top_doc.text.strip()
        citations = [f"[{doc.chunk_id}]" for doc in retrieved_docs[:2]]
        
        return (
            f"Based on the retrieved MSMARCO-XI evidence {', '.join(citations)}: "
            f"{doc_summary} "
            f"(Answer synthesized from top retrieved passage ID '{top_doc.chunk_id}')."
        )

def get_llm_provider(provider_name: str = None) -> LLMProvider:
    provider_name = (provider_name or config.LLM_PROVIDER).lower()
    if provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "ollama":
        return OllamaProvider()
    elif provider_name == "groq":
        return GroqProvider()
    elif provider_name == "mock":
        return MockGroundedLLMProvider()
    else:
        return GeminiProvider()
