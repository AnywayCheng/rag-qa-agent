import json
import re
from typing import Any

from . import config
from .embeddings import get_client

VALID_CATEGORIES = {"news", "paper", "github"}

_TOPIC_PROMPT = (
    "你是一個問題分類器。請把使用者的問題正規化成一個主題標籤，並判斷這個問題實際想查詢"
    "news（新聞）、paper（論文期刊）、github（開源工具/skill）中的哪幾個面向。"
    "如果問題籠統（例如「最新資訊」），三個面向都要包含。"
    '只能回傳一個 JSON 物件，格式為：{{"topic_key": "英文小寫底線分隔的正規化主題", '
    '"categories": ["news", "paper", "github"]}}，不要有其他文字。\n\n使用者問題：{question}'
)


def normalize(question: str, client: Any | None = None) -> dict:
    """把使用者問句轉成 {topic_key, categories}。解析失敗時降級為保守預設值（三面向都查）。"""
    client = client or get_client()
    interaction = client.interactions.create(
        model=config.GENERATION_MODEL,
        input=_TOPIC_PROMPT.format(question=question),
    )
    raw_text = getattr(interaction, "output_text", "") or ""
    return _parse_topic_response(raw_text) or _fallback_topic(question)


def _parse_topic_response(raw_text: str) -> dict | None:
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None

    topic_key = data.get("topic_key")
    categories = data.get("categories")
    if not isinstance(topic_key, str) or not topic_key.strip():
        return None
    if not isinstance(categories, list):
        return None

    filtered = [c for c in categories if c in VALID_CATEGORIES]
    if not filtered:
        return None

    return {"topic_key": slugify(topic_key), "categories": filtered}


def _fallback_topic(question: str) -> dict:
    return {"topic_key": slugify(question), "categories": sorted(VALID_CATEGORIES)}


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w一-鿿_]", "", text)
    return text or "untitled_topic"
