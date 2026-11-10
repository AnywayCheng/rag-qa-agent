from typing import Any

from . import config
from .embeddings import get_client

CATEGORY_PROMPTS = {
    "news": "搜尋關於「{topic}」的最新新聞報導",
    "paper": (
        "搜尋關於「{topic}」的最新學術論文或期刊研究，優先參考 arXiv、PubMed、Google Scholar "
        "等學術來源 site:arxiv.org OR site:pubmed.ncbi.nlm.nih.gov OR site:scholar.google.com"
    ),
    "github": "搜尋 GitHub 上關於「{topic}」的最新工具、repository 或 skill，site:github.com",
}


def search_category(topic: str, category: str, client: Any | None = None) -> list[dict]:
    """呼叫 google_search grounding，只回傳有 url_citation 佐證的片段（防捏造規則）。"""
    if category not in CATEGORY_PROMPTS:
        raise ValueError(f"unknown category: {category}")

    client = client or get_client()
    prompt = CATEGORY_PROMPTS[category].format(topic=topic)
    interaction = client.interactions.create(
        model=config.GENERATION_MODEL,
        input=prompt,
        tools=[{"type": "google_search"}],
    )
    return _extract_cited_facts(interaction)


def _extract_cited_facts(interaction: Any) -> list[dict]:
    facts = []
    for step in getattr(interaction, "steps", None) or []:
        if getattr(step, "type", None) != "model_output":
            continue
        for block in getattr(step, "content", None) or []:
            if getattr(block, "type", None) != "text":
                continue
            text = block.text
            for annotation in getattr(block, "annotations", None) or []:
                if getattr(annotation, "type", None) != "url_citation":
                    continue
                cited_text = text[annotation.start_index : annotation.end_index]
                if not cited_text.strip():
                    continue
                facts.append(
                    {
                        "text": cited_text,
                        "source_url": annotation.url,
                        "source_title": getattr(annotation, "title", "") or "",
                    }
                )
    return facts
