from google import genai
from google.genai import types

from . import config

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def embed_query(text: str, client: genai.Client | None = None) -> list[float]:
    """問句 embedding，使用 RETRIEVAL_QUERY task_type。"""
    client = client or get_client()
    result = client.models.embed_content(
        model=config.EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return result.embeddings[0].values


def embed_documents(
    texts: list[str], client: genai.Client | None = None
) -> list[list[float]]:
    """文件 chunk embedding，使用 RETRIEVAL_DOCUMENT task_type，保留輸入順序。"""
    if not texts:
        return []

    client = client or get_client()
    result = client.models.embed_content(
        model=config.EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return [embedding.values for embedding in result.embeddings]
