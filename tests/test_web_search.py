from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from rag_qa import web_search


def _annotation(type_, start_index=0, end_index=0, url="", title=""):
    return SimpleNamespace(
        type=type_, start_index=start_index, end_index=end_index, url=url, title=title
    )


def _text_block(text, annotations=None):
    return SimpleNamespace(type="text", text=text, annotations=annotations or [])


def _model_output_step(content_blocks):
    return SimpleNamespace(type="model_output", content=content_blocks)


def _make_mock_client(interaction):
    mock_client = MagicMock()
    mock_client.interactions.create.return_value = interaction
    return mock_client


def test_search_category_rejects_unknown_category():
    with pytest.raises(ValueError):
        web_search.search_category("AI", "unknown_category", client=MagicMock())


def test_search_category_returns_only_cited_spans():
    text = "生醫領域出現新突破，詳見報導。"
    annotation = _annotation(
        "url_citation",
        start_index=0,
        end_index=7,
        url="https://news.example.com/a",
        title="新聞A",
    )
    interaction = SimpleNamespace(
        steps=[_model_output_step([_text_block(text, [annotation])])]
    )
    client = _make_mock_client(interaction)

    facts = web_search.search_category("生醫", "news", client=client)

    assert len(facts) == 1
    assert facts[0]["text"] == text[0:7]
    assert facts[0]["source_url"] == "https://news.example.com/a"
    assert facts[0]["source_title"] == "新聞A"


def test_search_category_uses_correct_prompt_template_and_tool():
    interaction = SimpleNamespace(steps=[])
    client = _make_mock_client(interaction)

    web_search.search_category("量子電腦", "github", client=client)

    _, kwargs = client.interactions.create.call_args
    assert "量子電腦" in kwargs["input"]
    assert "site:github.com" in kwargs["input"]
    assert kwargs["tools"] == [{"type": "google_search"}]


def test_search_category_with_no_citations_returns_empty_list():
    text = "這句話沒有引用來源佐證。"
    interaction = SimpleNamespace(
        steps=[_model_output_step([_text_block(text, annotations=[])])]
    )
    client = _make_mock_client(interaction)

    facts = web_search.search_category("主題", "paper", client=client)

    assert facts == []


def test_search_category_ignores_non_model_output_steps():
    annotation = _annotation(
        "url_citation", start_index=0, end_index=2, url="https://x.com", title="X"
    )
    interaction = SimpleNamespace(
        steps=[
            SimpleNamespace(type="function_call", content=[]),
            _model_output_step([_text_block("ab有citation", [annotation])]),
        ]
    )
    client = _make_mock_client(interaction)

    facts = web_search.search_category("主題", "news", client=client)

    assert len(facts) == 1


def test_search_category_paper_prompt_includes_academic_sites():
    interaction = SimpleNamespace(steps=[])
    client = _make_mock_client(interaction)

    web_search.search_category("蛋白質摺疊", "paper", client=client)

    _, kwargs = client.interactions.create.call_args
    assert "arxiv.org" in kwargs["input"]
