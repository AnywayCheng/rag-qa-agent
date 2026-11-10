from unittest.mock import MagicMock

from rag_qa import ui


def test_format_answer_includes_answer_text():
    result = {"answer": "這是回答", "sources": [], "searched_categories": []}

    formatted = ui.format_answer(result)

    assert "這是回答" in formatted


def test_format_answer_includes_source_links():
    result = {
        "answer": "這是回答",
        "sources": [{"source_url": "https://x.com/a", "source_title": "文章A"}],
        "searched_categories": [],
    }

    formatted = ui.format_answer(result)

    assert "[文章A](https://x.com/a)" in formatted


def test_format_answer_notes_searched_categories():
    result = {
        "answer": "回答",
        "sources": [],
        "searched_categories": ["news", "github"],
    }

    formatted = ui.format_answer(result)

    assert "news" in formatted
    assert "github" in formatted


def test_format_answer_no_sources_section_when_empty():
    result = {"answer": "回答", "sources": [], "searched_categories": []}

    formatted = ui.format_answer(result)

    assert "來源" not in formatted


def test_chat_fn_calls_agent_ask_and_formats_result(monkeypatch):
    mock_ask = MagicMock(
        return_value={"answer": "回答內容", "sources": [], "searched_categories": []}
    )
    monkeypatch.setattr("rag_qa.ui.agent.ask", mock_ask)

    response = ui.chat_fn("問題", [])

    mock_ask.assert_called_once_with("問題")
    assert "回答內容" in response


def test_chat_fn_returns_friendly_message_on_exception(monkeypatch):
    monkeypatch.setattr(
        "rag_qa.ui.agent.ask", MagicMock(side_effect=RuntimeError("API 掛了"))
    )

    response = ui.chat_fn("問題", [])

    assert "錯誤" in response
    assert "API 掛了" in response


def test_handle_ingest_files_with_no_files_returns_message():
    assert "沒有選擇" in ui.handle_ingest_files(None)
    assert "沒有選擇" in ui.handle_ingest_files([])


def test_handle_ingest_files_reports_chunk_counts_per_file(monkeypatch, tmp_path):
    file_a = tmp_path / "a.txt"
    file_a.write_text("內容", encoding="utf-8")
    file_b = tmp_path / "b.md"
    file_b.write_text("內容", encoding="utf-8")

    mock_ingest = MagicMock(side_effect=[3, 1])
    monkeypatch.setattr("rag_qa.ui.ingest.ingest_local_file", mock_ingest)

    result = ui.handle_ingest_files([str(file_a), str(file_b)])

    assert "a.txt: 3 chunks" in result
    assert "b.md: 1 chunks" in result


def test_handle_ingest_files_returns_friendly_message_on_exception(
    monkeypatch, tmp_path
):
    file_a = tmp_path / "a.txt"
    file_a.write_text("內容", encoding="utf-8")
    monkeypatch.setattr(
        "rag_qa.ui.ingest.ingest_local_file",
        MagicMock(side_effect=RuntimeError("embedding 失敗")),
    )

    result = ui.handle_ingest_files([str(file_a)])

    assert "失敗" in result
    assert "embedding 失敗" in result


def test_handle_refresh_with_empty_topic_returns_message():
    assert "請輸入主題" in ui.handle_refresh("", ["news"])
    assert "請輸入主題" in ui.handle_refresh("   ", ["news"])


def test_handle_refresh_normalizes_topic_and_reports_result(monkeypatch):
    mock_refresh = MagicMock(return_value=["news", "github"])
    monkeypatch.setattr("rag_qa.ui.agent.refresh_topic", mock_refresh)

    result = ui.handle_refresh("AI Tools", ["news", "github"])

    mock_refresh.assert_called_once_with(
        "ai_tools", categories=["news", "github"], collection=None, client=None
    )
    assert "ai_tools" in result
    assert "news" in result


def test_handle_refresh_empty_category_list_defaults_to_none(monkeypatch):
    mock_refresh = MagicMock(return_value=["news", "paper", "github"])
    monkeypatch.setattr("rag_qa.ui.agent.refresh_topic", mock_refresh)

    ui.handle_refresh("AI", [])

    mock_refresh.assert_called_once_with(
        "ai", categories=None, collection=None, client=None
    )


def test_handle_refresh_returns_friendly_message_on_exception(monkeypatch):
    monkeypatch.setattr(
        "rag_qa.ui.agent.refresh_topic",
        MagicMock(side_effect=RuntimeError("搜尋失敗")),
    )

    result = ui.handle_refresh("AI", ["news"])

    assert "失敗" in result
    assert "搜尋失敗" in result
