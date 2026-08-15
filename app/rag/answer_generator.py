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

class GroqProvider(LLMProvider):
    """Groq LLM provider using ultra-fast Llama-3 inference."""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.GROQ_API_KEY
        self.model = model or "llama-3.1-8b-instant"

    def generate(self, question: str, retrieved_docs: List[SearchResultItem], history_context: str = "") -> str:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured in .env.")

        user_content = build_rag_prompt(question, retrieved_docs)
        if history_context:
            user_content = f"Conversation History:\n{history_context}\n\n{user_content}"

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
            "temperature": 0.3,
            "max_tokens": 1024
        }

        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.GEMINI_API_KEY or config.LLM_API_KEY
        self.model = model or "gemini-1.5-flash"

    def generate(self, question: str, retrieved_docs: List[SearchResultItem], history_context: str = "") -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in .env.")

        user_content = build_rag_prompt(question, retrieved_docs)
        if history_context:
            user_content = f"Conversation History:\n{history_context}\n\n{user_content}"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{SYSTEM_PROMPT}\n\n{user_content}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1024
            }
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=25)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()
        raise ValueError("Invalid Gemini response structure.")

class MockGroundedLLMProvider(LLMProvider):
    """Mock grounded synthesizer for testing purposes."""
    def generate(self, question: str, retrieved_docs: List[SearchResultItem], history_context: str = "") -> str:
        if not retrieved_docs:
            return "No relevant passages found."
        top_doc = retrieved_docs[0]
        return f"Based on [{top_doc.chunk_id}]: {top_doc.text}"

class ResilientLLMProvider(LLMProvider):
    """Orchestrates primary LLM provider with automatic multi-tiered fallback."""
    def __init__(self):
        self.primary_name = (config.LLM_PROVIDER or "groq").lower()

    def generate(self, question: str, retrieved_docs: List[SearchResultItem], history_context: str = "") -> str:
        if self.primary_name == "mock":
            return MockGroundedLLMProvider().generate(question, retrieved_docs, history_context)

        # Try Groq first
        if config.GROQ_API_KEY:
            try:
                return GroqProvider().generate(question, retrieved_docs, history_context)
            except Exception as e:
                logger.warning(f"Groq generation failed ({e}). Attempting fallback to Gemini...")

        # Try Gemini second
        if config.GEMINI_API_KEY:
            try:
                return GeminiProvider().generate(question, retrieved_docs, history_context)
            except Exception as e:
                logger.warning(f"Gemini generation failed: {e}.")

        # Fallback to extractive summary if all cloud LLMs are unavailable
        if retrieved_docs:
            top_passages = retrieved_docs[:3]
            bullets = "\n".join([f"• [{doc.chunk_id}] {doc.text}" for doc in top_passages])
            return (
                f"Based on the knowledge corpus evidence:\n\n{bullets}\n\n"
                f"(Retrieved from top matching passages: {', '.join([d.chunk_id for d in top_passages])})"
            )

        return "No relevant passages were found in the knowledge archive to answer this query."

def get_llm_provider(provider_name: str = None) -> LLMProvider:
    provider = (provider_name or config.LLM_PROVIDER or "groq").lower()
    if provider == "mock":
        return MockGroundedLLMProvider()
    return ResilientLLMProvider()
