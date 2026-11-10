from datetime import UTC, datetime
from typing import Any

from . import config, generator, github_meta, ingest, retriever, topic, web_search

ALL_CATEGORIES = sorted(web_search.CATEGORY_PROMPTS.keys())


def _is_fresh(fetched_at: str | None) -> bool:
    if fetched_at is None:
        return False
    fetched_dt = datetime.fromisoformat(fetched_at)
    if fetched_dt.tzinfo is None:
        fetched_dt = fetched_dt.replace(tzinfo=UTC)
    age_hours = (datetime.now(UTC) - fetched_dt).total_seconds() / 3600
    return age_hours < config.FRESHNESS_TTL_HOURS


def _refresh_category(
    topic_key: str, category: str, collection: Any, client: Any
) -> None:
    facts = web_search.search_category(topic_key, category, client=client)
    if category == "github":
        for fact in facts:
            fact["extra_metadata"] = github_meta.fetch_repo_metadata(fact["source_url"])
    ingest.overwrite_topic_category(topic_key, category, facts, collection=collection)


def ask(
    question: str,
    collection: Any | None = None,
    client: Any | None = None,
    force_refresh: bool = False,
    categories: list[str] | None = None,
) -> dict:
    """核心 orchestration：正規化問題 → 逐 category 查新鮮度 → 過期則搜尋+覆蓋 → 生成回答。"""
    collection = collection if collection is not None else retriever.get_collection()

    topic_result = topic.normalize(question, client=client)
    topic_key = topic_result["topic_key"]
    target_categories = categories or topic_result["categories"]

    searched: list[str] = []
    for category in target_categories:
        fetched_at = retriever.latest_fetched_at(
            topic_key, category, collection=collection
        )
        if force_refresh or not _is_fresh(fetched_at):
            _refresh_category(topic_key, category, collection, client)
            searched.append(category)

    chunks: list[dict] = []
    for category in target_categories:
        chunks.extend(
            retriever.query(question, category=category, collection=collection)
        )
    chunks.extend(
        retriever.query(question, category="local_file", collection=collection)
    )

    result = generator.generate_answer(question, chunks, client=client)
    result.update(
        {
            "topic_key": topic_key,
            "categories": target_categories,
            "searched_categories": searched,
        }
    )
    return result


def refresh_topic(
    topic_key: str,
    categories: list[str] | None = None,
    collection: Any | None = None,
    client: Any | None = None,
) -> list[str]:
    """手動強制刷新（CLI 的 refresh 指令用），不管 TTL。回傳實際刷新的 category 清單。"""
    collection = collection if collection is not None else retriever.get_collection()
    target_categories = categories or ALL_CATEGORIES
    for category in target_categories:
        _refresh_category(topic_key, category, collection, client)
    return target_categories
