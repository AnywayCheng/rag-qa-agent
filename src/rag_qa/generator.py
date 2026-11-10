from typing import Any

from . import config
from .embeddings import get_client

GITHUB_DISCLAIMER = "以上工具未經本系統資安審查，是否安裝／使用請自行評估來源可信度。"

_ANSWER_PROMPT = (
    "你是一個只根據下方提供的參考資料回答問題的助理。規則：\n"
    "1. 只能根據參考資料作答，不能編造參考資料以外的內容\n"
    "2. 回答中每個論點都要標明是根據哪個 [來源N]\n"
    "3. 如果參考資料不足以回答問題，直接說明查無相關資料，不要猜測\n"
    "4. 如果參考資料裡包含 GitHub 工具，只能陳述提供的客觀數據（star數/最後更新/license），"
    "絕對不能自己判斷或宣稱這個工具「安全」「值得信賴」\n\n"
    "參考資料：\n{context}\n\n問題：{question}"
)


def _format_github_stats(meta: dict) -> str:
    stats = []
    if meta.get("repo_stars") is not None:
        stats.append(f"star數：{meta['repo_stars']}")
    if meta.get("repo_last_push"):
        stats.append(f"最後更新：{meta['repo_last_push']}")
    if meta.get("repo_license"):
        stats.append(f"license：{meta['repo_license']}")
    if meta.get("repo_archived") is not None:
        stats.append(f"是否已封存：{'是' if meta['repo_archived'] else '否'}")
    return "、".join(stats)


def _format_context_block(chunks: list[dict]) -> str:
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk["metadata"]
        lines.append(f"[來源{i}] {chunk['document']}")
        if meta.get("source_url"):
            lines.append(f"    連結：{meta['source_url']}")
        if meta.get("category") == "github":
            stats = _format_github_stats(meta)
            if stats:
                lines.append(f"    {stats}")
    return "\n".join(lines)


def generate_answer(
    question: str, chunks: list[dict], client: Any | None = None
) -> dict:
    """組 prompt（含來源引用）呼叫 Gemini 生成回答。回傳 {answer, sources}。"""
    if not chunks:
        return {"answer": "目前查無相關資料可以回答這個問題。", "sources": []}

    client = client or get_client()
    prompt = _ANSWER_PROMPT.format(
        context=_format_context_block(chunks), question=question
    )
    interaction = client.interactions.create(
        model=config.GENERATION_MODEL, input=prompt
    )
    answer = getattr(interaction, "output_text", "") or ""

    has_github = any(chunk["metadata"].get("category") == "github" for chunk in chunks)
    if has_github and GITHUB_DISCLAIMER not in answer:
        answer = f"{answer}\n\n{GITHUB_DISCLAIMER}"

    sources = [
        {
            "source_url": chunk["metadata"]["source_url"],
            "source_title": chunk["metadata"].get("source_title"),
        }
        for chunk in chunks
        if chunk["metadata"].get("source_url")
    ]

    return {"answer": answer, "sources": sources}
