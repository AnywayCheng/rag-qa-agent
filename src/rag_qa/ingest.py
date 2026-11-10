from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from . import chunking, config, embeddings
from .retriever import get_collection, topic_category_filter

SUPPORTED_LOCAL_EXTENSIONS = {".pdf", ".txt", ".md"}


def _read_file_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8")


def ingest_local_file(path: Path, collection: Any | None = None) -> int:
    """讀取單一本地文件、切 chunk、embedding 後寫入 Chroma。回傳寫入的 chunk 數。"""
    collection = collection if collection is not None else get_collection()
    text = _read_file_text(path)
    chunks = chunking.chunk_text(
        text, chunk_size=config.CHUNK_SIZE, overlap=config.CHUNK_OVERLAP
    )
    if not chunks:
        return 0

    vectors = embeddings.embed_documents(chunks)
    ids = [f"local::{path.name}::{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "source": "local_file",
            "category": "local_file",
            "source_title": path.name,
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]
    collection.upsert(
        ids=ids, embeddings=vectors, documents=chunks, metadatas=metadatas
    )
    return len(chunks)


def ingest_directory(directory: Path, collection: Any | None = None) -> dict[str, int]:
    """批次 ingest 目錄下所有支援格式（pdf/txt/md）的文件。回傳 {檔名: chunk數}。"""
    collection = collection if collection is not None else get_collection()
    results: dict[str, int] = {}
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_LOCAL_EXTENSIONS:
            results[path.name] = ingest_local_file(path, collection=collection)
    return results


def overwrite_topic_category(
    topic_key: str,
    category: str,
    facts: list[dict],
    collection: Any | None = None,
) -> int:
    """網路搜尋結果覆蓋寫入：先刪除同 topic_key+category 的舊資料，再插入新的。
    每筆 fact 需含 text/source_url/source_title，可選 extra_metadata（例如 GitHub 客觀指標）。
    """
    collection = collection if collection is not None else get_collection()

    existing = collection.get(where=topic_category_filter(topic_key, category))
    if existing.get("ids"):
        collection.delete(ids=existing["ids"])

    if not facts:
        return 0

    texts = [fact["text"] for fact in facts]
    vectors = embeddings.embed_documents(texts)
    fetched_at = datetime.now(UTC).isoformat()

    ids = [f"web::{topic_key}::{category}::{i}" for i in range(len(facts))]
    metadatas = []
    for fact in facts:
        meta = {
            "source": "web",
            "topic_key": topic_key,
            "category": category,
            "fetched_at": fetched_at,
            "source_url": fact.get("source_url", ""),
            "source_title": fact.get("source_title", ""),
        }
        extra = fact.get("extra_metadata") or {}
        meta.update({k: v for k, v in extra.items() if v is not None})
        metadatas.append(meta)

    collection.upsert(ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas)
    return len(facts)
