from unittest.mock import MagicMock

import requests

from rag_qa import github_meta


def test_parse_owner_repo_basic_url():
    assert github_meta.parse_owner_repo("https://github.com/foo/bar") == ("foo", "bar")


def test_parse_owner_repo_strips_git_suffix():
    assert github_meta.parse_owner_repo("https://github.com/foo/bar.git") == (
        "foo",
        "bar",
    )


def test_parse_owner_repo_with_subpath():
    url = "https://github.com/foo/bar/blob/main/README.md"
    assert github_meta.parse_owner_repo(url) == ("foo", "bar")


def test_parse_owner_repo_returns_none_for_non_github_url():
    assert github_meta.parse_owner_repo("https://example.com/foo/bar") is None


def _mock_response(status_code=200, json_data=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    return response


def test_fetch_repo_metadata_returns_objective_signals_on_success():
    session = MagicMock()
    session.get.return_value = _mock_response(
        200,
        {
            "stargazers_count": 123,
            "pushed_at": "2026-09-01T00:00:00Z",
            "license": {"spdx_id": "MIT"},
            "archived": False,
        },
    )

    result = github_meta.fetch_repo_metadata(
        "https://github.com/foo/bar", session=session
    )

    assert result == {
        "repo_stars": 123,
        "repo_last_push": "2026-09-01T00:00:00Z",
        "repo_license": "MIT",
        "repo_archived": False,
    }


def test_fetch_repo_metadata_returns_empty_dict_on_non_200():
    session = MagicMock()
    session.get.return_value = _mock_response(404)

    result = github_meta.fetch_repo_metadata(
        "https://github.com/foo/bar", session=session
    )

    assert result == {}


def test_fetch_repo_metadata_returns_empty_dict_on_network_error():
    session = MagicMock()
    session.get.side_effect = requests.RequestException("boom")

    result = github_meta.fetch_repo_metadata(
        "https://github.com/foo/bar", session=session
    )

    assert result == {}


def test_fetch_repo_metadata_returns_empty_dict_for_unparsable_url_without_calling_api():
    session = MagicMock()

    result = github_meta.fetch_repo_metadata(
        "https://example.com/not-github", session=session
    )

    assert result == {}
    session.get.assert_not_called()


def test_fetch_repo_metadata_sends_auth_header_when_token_configured(monkeypatch):
    monkeypatch.setattr(github_meta.config, "GITHUB_TOKEN", "fake-token")
    session = MagicMock()
    session.get.return_value = _mock_response(200, {})

    github_meta.fetch_repo_metadata("https://github.com/foo/bar", session=session)

    _, kwargs = session.get.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer fake-token"
