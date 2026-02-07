"""LLM integration package for AEGIS.

This package provides clients for interacting with various LLM backends:
- Ollama: Local LLM inference (CPU/GPU)
- Groq: Fast cloud API
- Gemini: Google Gemini API
"""

from aegis.agent.llm.gemini import GeminiClient, get_gemini_client
from aegis.agent.llm.groq import GroqClient, get_groq_client
from aegis.agent.llm.ollama import OllamaClient, get_ollama_client
from aegis.agent.llm.router import chat_with_schema_with_fallback

__all__ = [
    "GeminiClient",
    "GroqClient",
    "OllamaClient",
    "chat_with_schema_with_fallback",
    "get_gemini_client",
    "get_groq_client",
    "get_ollama_client",
]
