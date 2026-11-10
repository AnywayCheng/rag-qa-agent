from types import SimpleNamespace
from unittest.mock import MagicMock

from rag_qa import generator


def _make_mock_client(output_text):
    client = MagicMock()
    client.interactions.create.return_value = SimpleNamespace(output_text=output_text)
    return client


def _news_chunk(text="新聞內容", url="https://news.example.com/a", title="新聞A"):
    return {
        "document": text,
        "metadata": {"category": "news", "source_url": url, "source_title": title},
        "distance": 0.1,
    }


def _github_chunk():
    return {
        "document": "一個好用的 RAG 工具",
        "metadata": {
            "category": "github",
            "source_url": "https://github.com/foo/bar",
            "source_title": "foo/bar",
            "repo_stars": 100,
            "repo_last_push": "2026-09-01T00:00:00Z",
            "repo_license": "MIT",
            "repo_archived": False,
        },
        "distance": 0.2,
    }


def _local_file_chunk():
    return {
        "document": "本地文件內容",
        "metadata": {
            "category": "local_file",
            "source_url": "",
            "source_title": "note.txt",
        },
        "distance": 0.3,
    }


def test_generate_answer_with_no_chunks_returns_fixed_message_without_calling_api():
    client = MagicMock()

    result = generator.generate_answer("問題", [], client=client)

    assert "查無相關資料" in result["answer"]
    assert result["sources"] == []
    client.interactions.create.assert_not_called()


def test_generate_answer_includes_context_and_question_in_prompt():
    client = _make_mock_client("這是回答 [來源1]")

    generator.generate_answer("這是問題", [_news_chunk()], client=client)

    _, kwargs = client.interactions.create.call_args
    assert "這是問題" in kwargs["input"]
    assert "[來源1]" in kwargs["input"]
    assert "新聞內容" in kwargs["input"]


def test_generate_answer_collects_sources_from_chunks_with_url():
    client = _make_mock_client("回答內容")

    result = generator.generate_answer(
        "問題", [_news_chunk(), _local_file_chunk()], client=client
    )

    assert result["sources"] == [
        {"source_url": "https://news.example.com/a", "source_title": "新聞A"}
    ]


def test_generate_answer_appends_disclaimer_when_github_chunk_present_and_missing():
    client = _make_mock_client("這個工具很推薦")

    result = generator.generate_answer("有什麼工具", [_github_chunk()], client=client)

    assert generator.GITHUB_DISCLAIMER in result["answer"]


def test_generate_answer_does_not_duplicate_disclaimer_if_already_present():
    client = _make_mock_client(f"這是回答\n\n{generator.GITHUB_DISCLAIMER}")

    result = generator.generate_answer("有什麼工具", [_github_chunk()], client=client)

    assert result["answer"].count(generator.GITHUB_DISCLAIMER) == 1


def test_generate_answer_no_disclaimer_when_no_github_chunks():
    client = _make_mock_client("這是回答")

    result = generator.generate_answer("問題", [_news_chunk()], client=client)

    assert generator.GITHUB_DISCLAIMER not in result["answer"]


def test_generate_answer_context_includes_github_objective_stats():
    client = _make_mock_client("回答")

    generator.generate_answer("有什麼工具", [_github_chunk()], client=client)

    _, kwargs = client.interactions.create.call_args
    prompt = kwargs["input"]
    assert "100" in prompt
    assert "MIT" in prompt
