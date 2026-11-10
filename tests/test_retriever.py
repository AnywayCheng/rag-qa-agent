import uuid
from unittest.mock import patch

import chromadb

from rag_qa import retriever


def _make_test_collection():
    # chromadb.EphemeralClient() 實例間會共用同一個底層 in-memory store（同名 collection 會拿到
    # 同一份資料），每個測試用唯一 collection 名稱才能確保彼此隔離
    client = chromadb.EphemeralClient()
    return client.get_or_create_collection(f"test_collection_{uuid.uuid4().hex}")


@patch("rag_qa.embeddings.embed_query")
def test_query_returns_top_k_results_with_metadata(mock_embed_query):
    collection = _make_test_collection()
    collection.add(
        ids=["1", "2"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        documents=["doc about cats", "doc about dogs"],
        metadatas=[{"category": "news"}, {"category": "paper"}],
    )
    mock_embed_query.return_value = [1.0, 0.0]

    results = retriever.query("cats?", top_k=2, collection=collection)

    assert len(results) == 2
    assert results[0]["document"] == "doc about cats"
    assert results[0]["metadata"]["category"] == "news"


@patch("rag_qa.embeddings.embed_query")
def test_query_filters_by_category(mock_embed_query):
    collection = _make_test_collection()
    collection.add(
        ids=["1", "2"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        documents=["news doc", "paper doc"],
        metadatas=[{"category": "news"}, {"category": "paper"}],
    )
    mock_embed_query.return_value = [1.0, 0.0]

    results = retriever.query("x", top_k=5, category="paper", collection=collection)

    assert len(results) == 1
    assert results[0]["document"] == "paper doc"


def test_latest_fetched_at_returns_none_when_no_data():
    collection = _make_test_collection()

    assert retriever.latest_fetched_at("ai_news", "news", collection=collection) is None


def test_latest_fetched_at_returns_max_timestamp():
    collection = _make_test_collection()
    collection.add(
        ids=["1", "2"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        documents=["old", "new"],
        metadatas=[
            {
                "topic_key": "ai_news",
                "category": "news",
                "fetched_at": "2026-09-20T00:00:00",
            },
            {
                "topic_key": "ai_news",
                "category": "news",
                "fetched_at": "2026-09-22T00:00:00",
            },
        ],
    )

    result = retriever.latest_fetched_at("ai_news", "news", collection=collection)

    assert result == "2026-09-22T00:00:00"


def test_latest_fetched_at_ignores_other_topic_or_category():
    collection = _make_test_collection()
    collection.add(
        ids=["1", "2"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        documents=["unrelated topic", "unrelated category"],
        metadatas=[
            {
                "topic_key": "other_topic",
                "category": "news",
                "fetched_at": "2026-09-22T00:00:00",
            },
            {
                "topic_key": "ai_news",
                "category": "github",
                "fetched_at": "2026-09-22T00:00:00",
            },
        ],
    )

    assert retriever.latest_fetched_at("ai_news", "news", collection=collection) is None
