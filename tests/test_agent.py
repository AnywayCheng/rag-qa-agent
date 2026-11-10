import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import chromadb
import pytest

from rag_qa import agent


def _make_test_collection():
    client = chromadb.EphemeralClient()
    return client.get_or_create_collection(f"test_collection_{uuid.uuid4().hex}")


def _mock_topic(topic_key="ai_news", categories=None):
    categories = categories or ["news", "paper", "github"]
    return MagicMock(return_value={"topic_key": topic_key, "categories": categories})


@pytest.fixture(autouse=True)
def _mock_embeddings(monkeypatch):
    monkeypatch.setattr(
        "rag_qa.embeddings.embed_documents",
        lambda texts, client=None: [[float(len(t)) + i] for i, t in enumerate(texts)],
    )
    monkeypatch.setattr(
        "rag_qa.embeddings.embed_query", lambda text, client=None: [1.0]
    )


def _stub_generator(monkeypatch, answer="回答"):
    monkeypatch.setattr(
        "rag_qa.generator.generate_answer",
        MagicMock(return_value={"answer": answer, "sources": []}),
    )


def test_first_question_triggers_search_for_all_categories(monkeypatch):
    collection = _make_test_collection()
    monkeypatch.setattr("rag_qa.topic.normalize", _mock_topic())
    search_mock = MagicMock(
        return_value=[
            {"text": "新資料", "source_url": "https://x.com/1", "source_title": "t"}
        ]
    )
    monkeypatch.setattr("rag_qa.web_search.search_category", search_mock)
    monkeypatch.setattr(
        "rag_qa.github_meta.fetch_repo_metadata", MagicMock(return_value={})
    )
    _stub_generator(monkeypatch)

    result = agent.ask("AI 最新資訊", collection=collection)

    assert sorted(result["searched_categories"]) == ["github", "news", "paper"]
    assert search_mock.call_count == 3


def test_repeated_question_within_ttl_does_not_trigger_search(monkeypatch):
    collection = _make_test_collection()
    monkeypatch.setattr("rag_qa.topic.normalize", _mock_topic(categories=["news"]))
    search_mock = MagicMock(return_value=[])
    monkeypatch.setattr("rag_qa.web_search.search_category", search_mock)
    _stub_generator(monkeypatch)
    collection.add(
        ids=["1"],
        embeddings=[[1.0]],
        documents=["既有資料"],
        metadatas=[
            {
                "source": "web",
                "topic_key": "ai_news",
                "category": "news",
                "fetched_at": datetime.now(UTC).isoformat(),
                "source_url": "https://x.com",
                "source_title": "t",
            }
        ],
    )

    result = agent.ask("AI 最新資訊", collection=collection)

    assert result["searched_categories"] == []
    search_mock.assert_not_called()


def test_stale_data_triggers_search_and_overwrites_old_data(monkeypatch):
    collection = _make_test_collection()
    monkeypatch.setattr("rag_qa.topic.normalize", _mock_topic(categories=["news"]))
    search_mock = MagicMock(
        return_value=[
            {"text": "新資料", "source_url": "https://x.com/new", "source_title": "new"}
        ]
    )
    monkeypatch.setattr("rag_qa.web_search.search_category", search_mock)
    _stub_generator(monkeypatch)
    stale_time = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
    collection.add(
        ids=["old-1"],
        embeddings=[[1.0]],
        documents=["舊資料"],
        metadatas=[
            {
                "source": "web",
                "topic_key": "ai_news",
                "category": "news",
                "fetched_at": stale_time,
                "source_url": "https://x.com/old",
                "source_title": "old",
            }
        ],
    )

    result = agent.ask("AI 最新資訊", collection=collection)

    assert result["searched_categories"] == ["news"]
    stored_docs = collection.get()["documents"]
    assert "舊資料" not in stored_docs
    assert "新資料" in stored_docs


def test_search_with_no_citations_does_not_crash_and_writes_nothing(monkeypatch):
    collection = _make_test_collection()
    monkeypatch.setattr("rag_qa.topic.normalize", _mock_topic(categories=["news"]))
    monkeypatch.setattr("rag_qa.web_search.search_category", MagicMock(return_value=[]))
    _stub_generator(monkeypatch, answer="查無資料")

    result = agent.ask("AI 最新資訊", collection=collection)

    assert result["searched_categories"] == ["news"]
    assert collection.count() == 0


def test_github_category_fetches_repo_metadata_and_stores_it(monkeypatch):
    collection = _make_test_collection()
    monkeypatch.setattr("rag_qa.topic.normalize", _mock_topic(categories=["github"]))
    monkeypatch.setattr(
        "rag_qa.web_search.search_category",
        MagicMock(
            return_value=[
                {
                    "text": "一個好用的工具",
                    "source_url": "https://github.com/foo/bar",
                    "source_title": "foo/bar",
                }
            ]
        ),
    )
    monkeypatch.setattr(
        "rag_qa.github_meta.fetch_repo_metadata",
        MagicMock(return_value={"repo_stars": 42, "repo_license": "MIT"}),
    )
    _stub_generator(monkeypatch)

    agent.ask("有什麼好工具", collection=collection)

    stored = collection.get()
    meta = stored["metadatas"][0]
    assert meta["repo_stars"] == 42
    assert meta["repo_license"] == "MIT"


def test_force_refresh_bypasses_freshness_check(monkeypatch):
    collection = _make_test_collection()
    monkeypatch.setattr("rag_qa.topic.normalize", _mock_topic(categories=["news"]))
    search_mock = MagicMock(
        return_value=[{"text": "新資料", "source_url": "u", "source_title": "t"}]
    )
    monkeypatch.setattr("rag_qa.web_search.search_category", search_mock)
    _stub_generator(monkeypatch)
    collection.add(
        ids=["1"],
        embeddings=[[1.0]],
        documents=["既有資料"],
        metadatas=[
            {
                "source": "web",
                "topic_key": "ai_news",
                "category": "news",
                "fetched_at": datetime.now(UTC).isoformat(),
                "source_url": "u",
                "source_title": "t",
            }
        ],
    )

    result = agent.ask("AI 最新資訊", collection=collection, force_refresh=True)

    assert result["searched_categories"] == ["news"]
    search_mock.assert_called_once()


def test_refresh_topic_searches_all_three_categories_by_default(monkeypatch):
    collection = _make_test_collection()
    search_mock = MagicMock(return_value=[])
    monkeypatch.setattr("rag_qa.web_search.search_category", search_mock)

    refreshed = agent.refresh_topic("ai_news", collection=collection)

    assert sorted(refreshed) == ["github", "news", "paper"]
    assert search_mock.call_count == 3


def test_refresh_topic_can_target_single_category(monkeypatch):
    collection = _make_test_collection()
    search_mock = MagicMock(return_value=[])
    monkeypatch.setattr("rag_qa.web_search.search_category", search_mock)

    refreshed = agent.refresh_topic(
        "ai_news", categories=["github"], collection=collection
    )

    assert refreshed == ["github"]
    search_mock.assert_called_once()
