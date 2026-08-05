import os
from typing import Sequence
from loguru import logger

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_CHAT_MODEL = os.getenv("OPENROUTER_CHAT_MODEL", "deepseek/deepseek-chat")
OPENROUTER_EMBEDDING_MODEL = os.getenv("OPENROUTER_EMBEDDING_MODEL", "baai/bge-m3")

openrouter_client = None
_embedding_client = None


def _build_client():
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set")
    from openai import OpenAI

    return OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)


def get_chat_client():
    """Return a lazily-initialized OpenRouter client for chat completions."""
    global openrouter_client
    if openrouter_client is None:
        openrouter_client = _build_client()
        logger.info("Initialized OpenRouter chat client")
    return openrouter_client


def get_embedding_client():
    """Return a lazily-initialized OpenRouter client for embeddings."""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = _build_client()
        logger.info("Initialized OpenRouter embedding client")
    return _embedding_client


def chat(messages: list[dict], model: str | None = None) -> str:
    """Send a chat completion request and return the assistant message text."""
    client = get_chat_client()
    response = client.chat.completions.create(
        model=model or OPENROUTER_CHAT_MODEL,
        messages=messages,
    )
    return response.choices[0].message.content


def embed_texts(texts: Sequence[str], model: str | None = None) -> list[list[float]]:
    """Embed a batch of texts using OpenRouter's OpenAI-compatible embeddings API.

    Returns embeddings in the same order as the input (OpenRouter may return
    them out of order, so results are sorted by the ``index`` field).
    """
    texts = list(texts)
    if not texts:
        return []

    client = get_embedding_client()
    response = client.embeddings.create(
        model=model or OPENROUTER_EMBEDDING_MODEL,
        input=texts,
        encoding_format="float",
    )
    data = sorted(response.data, key=lambda item: item.index)
    return [item.embedding for item in data]
