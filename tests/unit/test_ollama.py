"""Test Ollama client."""

from aegis.agent.llm.ollama import OllamaClient, get_ollama_client


def test_get_ollama_client():
    """Test ollama client factory."""
    client = get_ollama_client()
    assert client is not None
    assert isinstance(client, OllamaClient)


def test_ollama_client_has_methods():
    """Test that client has required methods."""
    client = get_ollama_client()
    assert hasattr(client, "chat")
    assert hasattr(client, "chat_with_schema")
