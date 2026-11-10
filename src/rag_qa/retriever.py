from typing import Any

import chromadb

from . import config, embeddings

_client: chromadb.ClientAPI | None = None


def topic_category_filter(topic_key: str, category: str) -> dict:
    """給 ingest.py 的覆蓋邏輯共用：組出比對 topic_key+category 的 where 條件。"""
    return {"$and": [{"topic_key": topic_key}, {"category": category}]}


def get_collection() -> Any:
    """取得（或建立）persistent Chroma collection。"""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
    return _client.get_or_create_collection(config.CHROMA_COLLECTION_NAME)


def query(
    query_text: str,
    top_k: int = config.RETRIEVAL_TOP_K,
    category: str | None = None,
    collection: Any | None = None,
) -> list[dict]:
    """向量相似度查詢，回傳含 metadata 的結果，可選依 category 過濾。"""
    collection = collection if collection is not None else get_collection()
    query_embedding = embeddings.embed_query(query_text)
    where = {"category": category} if category else None

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
    )

    documents = result["documents"][0] if result["documents"] else []
    metadatas = result["metadatas"][0] if result["metadatas"] else []
    distances = result["distances"][0] if result["distances"] else []

    return [
        {"document": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]


def latest_fetched_at(
    topic_key: str, category: str, collection: Any | None = None
) -> str | None:
    """查某個 topic_key+category 目前最新的 fetched_at（ISO8601 字串排序即為時間排序）。"""
    collection = collection if collection is not None else get_collection()
    result = collection.get(where=topic_category_filter(topic_key, category))

    metadatas = result.get("metadatas") or []
    fetched_ats = [m.get("fetched_at") for m in metadatas if m.get("fetched_at")]
    if not fetched_ats:
        return None
    return max(fetched_ats)
