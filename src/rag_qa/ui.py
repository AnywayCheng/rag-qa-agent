from pathlib import Path
from typing import Any

import gradio as gr

from . import agent, ingest, topic


def format_answer(result: dict) -> str:
    """把 agent.ask() 的回傳結果格式化成聊天介面顯示用的 markdown。"""
    lines = [result["answer"]]

    if result.get("sources"):
        lines.append("\n**來源：**")
        for src in result["sources"]:
            title = src.get("source_title") or src["source_url"]
            lines.append(f"- [{title}]({src['source_url']})")

    if result.get("searched_categories"):
        searched = "、".join(result["searched_categories"])
        lines.append(f"\n_（本次重新搜尋了：{searched}）_")

    return "\n".join(lines)


def chat_fn(message: str, history: list) -> str:
    try:
        result = agent.ask(message)
        return format_answer(result)
    except Exception as exc:  # noqa: BLE001 - UI 邊界，需把任何錯誤轉成友善訊息
        return f"發生錯誤：{exc}"


def handle_ingest_files(
    file_paths: list[str] | None, collection: Any | None = None
) -> str:
    if not file_paths:
        return "沒有選擇任何檔案。"

    try:
        lines = []
        for file_path in file_paths:
            path = Path(file_path)
            count = ingest.ingest_local_file(path, collection=collection)
            lines.append(f"{path.name}: {count} chunks")
        return "\n".join(lines)
    except Exception as exc:  # noqa: BLE001
        return f"匯入失敗：{exc}"


def handle_refresh(
    topic_text: str,
    categories: list[str] | None,
    collection: Any | None = None,
    client: Any | None = None,
) -> str:
    if not topic_text or not topic_text.strip():
        return "請輸入主題。"

    try:
        topic_key = topic.slugify(topic_text)
        target_categories = categories or None
        refreshed = agent.refresh_topic(
            topic_key,
            categories=target_categories,
            collection=collection,
            client=client,
        )
        return f"已刷新主題「{topic_text}」（topic_key={topic_key}）：{', '.join(refreshed)}"
    except Exception as exc:  # noqa: BLE001
        return f"刷新失敗：{exc}"


def build_app() -> gr.Blocks:
    with gr.Blocks(title="RAG 知識庫問答 Agent") as demo:
        gr.Markdown("# RAG 知識庫問答 Agent\n本地文件 + 新聞/論文/GitHub 網路保鮮搜尋")

        with gr.Tabs():
            with gr.Tab("問答"):
                gr.ChatInterface(fn=chat_fn)

            with gr.Tab("匯入本地文件"):
                file_input = gr.File(
                    file_count="multiple",
                    file_types=[".pdf", ".txt", ".md"],
                    label="選擇文件（PDF/txt/md）",
                )
                ingest_button = gr.Button("匯入")
                ingest_output = gr.Textbox(label="結果", interactive=False)
                ingest_button.click(
                    fn=handle_ingest_files, inputs=[file_input], outputs=[ingest_output]
                )

            with gr.Tab("手動刷新"):
                topic_input = gr.Textbox(label="主題", placeholder="例如：AI 工具")
                category_checkboxes = gr.CheckboxGroup(
                    choices=["news", "paper", "github"],
                    value=["news", "paper", "github"],
                    label="面向（不勾選任何項目 = 三個都刷新）",
                )
                refresh_button = gr.Button("刷新")
                refresh_output = gr.Textbox(label="結果", interactive=False)
                refresh_button.click(
                    fn=handle_refresh,
                    inputs=[topic_input, category_checkboxes],
                    outputs=[refresh_output],
                )

    return demo


def main() -> None:
    build_app().launch()


if __name__ == "__main__":
    main()
