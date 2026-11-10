from unittest.mock import MagicMock

from rag_qa import cli


def _run(monkeypatch, argv, **mocks):
    for target, mock in mocks.items():
        monkeypatch.setattr(target, mock)
    parser = cli.build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def test_ingest_reports_missing_directory(tmp_path, capsys):
    missing_dir = tmp_path / "does_not_exist"
    parser = cli.build_parser()
    args = parser.parse_args(["ingest", str(missing_dir)])

    exit_code = args.func(args)

    assert exit_code == 1
    assert "目錄不存在" in capsys.readouterr().err


def test_ingest_reports_chunk_counts(monkeypatch, tmp_path, capsys):
    mock_ingest_directory = MagicMock(return_value={"a.txt": 3, "b.md": 1})
    exit_code = _run(
        monkeypatch,
        ["ingest", str(tmp_path)],
        **{"rag_qa.cli.ingest.ingest_directory": mock_ingest_directory},
    )

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "a.txt: 3 chunks" in out
    assert "b.md: 1 chunks" in out


def test_ask_prints_answer_sources_and_searched_categories(monkeypatch, capsys):
    mock_ask = MagicMock(
        return_value={
            "answer": "這是回答",
            "sources": [{"source_url": "https://x.com", "source_title": "X"}],
            "searched_categories": ["news"],
        }
    )
    exit_code = _run(monkeypatch, ["ask", "問題"], **{"rag_qa.cli.agent.ask": mock_ask})

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "這是回答" in out
    assert "https://x.com" in out
    assert "news" in out
    mock_ask.assert_called_once_with("問題", force_refresh=False)


def test_ask_passes_refresh_flag(monkeypatch):
    mock_ask = MagicMock(
        return_value={"answer": "a", "sources": [], "searched_categories": []}
    )
    _run(
        monkeypatch,
        ["ask", "問題", "--refresh"],
        **{"rag_qa.cli.agent.ask": mock_ask},
    )

    mock_ask.assert_called_once_with("問題", force_refresh=True)


def test_refresh_normalizes_topic_and_defaults_to_all_categories(monkeypatch, capsys):
    mock_refresh = MagicMock(return_value=["news", "paper", "github"])
    exit_code = _run(
        monkeypatch,
        ["refresh", "AI Tools News"],
        **{"rag_qa.cli.agent.refresh_topic": mock_refresh},
    )

    out = capsys.readouterr().out
    assert exit_code == 0
    mock_refresh.assert_called_once_with("ai_tools_news", categories=None)
    assert "ai_tools_news" in out


def test_refresh_with_specific_category(monkeypatch):
    mock_refresh = MagicMock(return_value=["github"])
    _run(
        monkeypatch,
        ["refresh", "AI Tools", "--category", "github"],
        **{"rag_qa.cli.agent.refresh_topic": mock_refresh},
    )

    mock_refresh.assert_called_once_with("ai_tools", categories=["github"])
