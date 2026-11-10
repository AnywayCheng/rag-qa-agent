import uuid
from unittest.mock import patch

import chromadb
import pytest

from rag_qa import ingest


def _make_test_collection():
    client = chromadb.EphemeralClient()
    return client.get_or_create_collection(f"test_collection_{uuid.uuid4().hex}")


@pytest.fixture(autouse=True)
def _mock_embeddings():
    with patch("rag_qa.embeddings.embed_documents") as mock:
        mock.side_effect = lambda texts: [[float(len(t))] for t in texts]
        yield mock


def test_ingest_local_file_writes_chunks_with_local_file_metadata(tmp_path):
    collection = _make_test_collection()
    file_path = tmp_path / "note.txt"
    file_path.write_text("這是一份測試筆記內容。" * 5, encoding="utf-8")

    count = ingest.ingest_local_file(file_path, collection=collection)

    assert count >= 1
    stored = collection.get()
    assert len(stored["ids"]) == count
    for meta in stored["metadatas"]:
        assert meta["source"] == "local_file"
        assert meta["category"] == "local_file"
        assert meta["source_title"] == "note.txt"


def test_ingest_local_file_empty_file_writes_nothing(tmp_path):
    collection = _make_test_collection()
    file_path = tmp_path / "empty.txt"
    file_path.write_text("   ", encoding="utf-8")

    count = ingest.ingest_local_file(file_path, collection=collection)

    assert count == 0
    assert collection.count() == 0


def test_ingest_directory_only_processes_supported_extensions(tmp_path):
    collection = _make_test_collection()
    (tmp_path / "a.txt").write_text("內容一二三四五", encoding="utf-8")
    (tmp_path / "b.md").write_text("內容六七八九十", encoding="utf-8")
    (tmp_path / "ignore.exe").write_bytes(b"\x00\x01")

    results = ingest.ingest_directory(tmp_path, collection=collection)

    assert set(results.keys()) == {"a.txt", "b.md"}


def test_overwrite_topic_category_deletes_old_before_inserting_new(monkeypatch):
    collection = _make_test_collection()
    collection.add(
        ids=["old-1"],
        embeddings=[[1.0]],
        documents=["舊資料"],
        metadatas=[
            {
                "topic_key": "ai_news",
                "category": "news",
                "fetched_at": "2020-01-01T00:00:00",
            }
        ],
    )

    facts = [
        {
            "text": "新新聞內容",
            "source_url": "https://example.com/a",
            "source_title": "A",
        },
        {
            "text": "第二則新聞",
            "source_url": "https://example.com/b",
            "source_title": "B",
        },
    ]
    count = ingest.overwrite_topic_category(
        "ai_news", "news", facts, collection=collection
    )

    assert count == 2
    stored = collection.get()
    documents = stored["documents"]
    assert "舊資料" not in documents
    assert "新新聞內容" in documents
    assert "第二則新聞" in documents
    for meta in stored["metadatas"]:
        assert meta["source"] == "web"
        assert meta["topic_key"] == "ai_news"
        assert meta["category"] == "news"
        assert "fetched_at" in meta


def test_overwrite_topic_category_does_not_touch_other_category():
    collection = _make_test_collection()
    collection.add(
        ids=["gh-1"],
        embeddings=[[1.0]],
        documents=["github 資料"],
        metadatas=[
            {
                "topic_key": "ai_news",
                "category": "github",
                "fetched_at": "2020-01-01T00:00:00",
            }
        ],
    )

    ingest.overwrite_topic_category(
        "ai_news",
        "news",
        [{"text": "新新聞", "source_url": "u", "source_title": "t"}],
        collection=collection,
    )

    stored = collection.get()
    assert "github 資料" in stored["documents"]


def test_overwrite_topic_category_with_empty_facts_only_clears_old_data():
    collection = _make_test_collection()
    collection.add(
        ids=["old-1"],
        embeddings=[[1.0]],
        documents=["舊資料"],
        metadatas=[
            {
                "topic_key": "ai_news",
                "category": "news",
                "fetched_at": "2020-01-01T00:00:00",
            }
        ],
    )

    count = ingest.overwrite_topic_category(
        "ai_news", "news", [], collection=collection
    )

    assert count == 0
    assert collection.count() == 0


def test_overwrite_topic_category_merges_extra_metadata_and_drops_none_values():
    collection = _make_test_collection()
    facts = [
        {
            "text": "github repo 介紹",
            "source_url": "https://github.com/foo/bar",
            "source_title": "foo/bar",
            "extra_metadata": {"repo_stars": 42, "repo_license": None},
        }
    ]

    ingest.overwrite_topic_category("ai_tools", "github", facts, collection=collection)

    stored = collection.get()
    meta = stored["metadatas"][0]
    assert meta["repo_stars"] == 42
    assert "repo_license" not in meta
