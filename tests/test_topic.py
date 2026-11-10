from types import SimpleNamespace
from unittest.mock import MagicMock

from rag_qa import topic


def _make_mock_client(output_text):
    client = MagicMock()
    client.interactions.create.return_value = SimpleNamespace(output_text=output_text)
    return client


def test_normalize_parses_valid_json_response():
    client = _make_mock_client(
        '{"topic_key": "biomedical_news", "categories": ["news", "paper"]}'
    )

    result = topic.normalize("生醫最新資訊", client=client)

    assert result == {"topic_key": "biomedical_news", "categories": ["news", "paper"]}


def test_normalize_parses_json_wrapped_in_markdown_fence():
    client = _make_mock_client(
        '這是分析結果：\n```json\n{"topic_key": "ai_tools", "categories": ["github"]}\n```'
    )

    result = topic.normalize("有什麼新的 AI 工具", client=client)

    assert result == {"topic_key": "ai_tools", "categories": ["github"]}


def test_normalize_filters_out_invalid_categories():
    client = _make_mock_client(
        '{"topic_key": "quantum_computing", "categories": ["news", "invalid_category"]}'
    )

    result = topic.normalize("量子電腦", client=client)

    assert result == {"topic_key": "quantum_computing", "categories": ["news"]}


def test_normalize_falls_back_when_response_is_not_json():
    client = _make_mock_client("我不太確定你在問什麼")

    result = topic.normalize("Some Ambiguous Question", client=client)

    assert result["categories"] == sorted({"news", "paper", "github"})
    assert result["topic_key"]


def test_normalize_falls_back_when_topic_key_missing():
    client = _make_mock_client('{"categories": ["news"]}')

    result = topic.normalize("測試問題", client=client)

    assert result["categories"] == sorted({"news", "paper", "github"})


def test_normalize_falls_back_when_all_categories_invalid():
    client = _make_mock_client('{"topic_key": "x", "categories": ["not_real"]}')

    result = topic.normalize("測試問題", client=client)

    assert result["categories"] == sorted({"news", "paper", "github"})


def test_slugify_converts_spaces_and_strips_punctuation():
    assert topic.slugify("AI Tools News!!") == "ai_tools_news"


def test_slugify_keeps_chinese_characters():
    assert topic.slugify("生醫 最新資訊") == "生醫_最新資訊"


def test_slugify_empty_string_has_safe_fallback():
    assert topic.slugify("   ") == "untitled_topic"
