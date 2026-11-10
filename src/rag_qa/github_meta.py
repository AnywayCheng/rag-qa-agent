import re
from typing import Any

import requests

from . import config

_GITHUB_REPO_URL_RE = re.compile(r"github\.com/([^/]+)/([^/?#]+)")


def parse_owner_repo(url: str) -> tuple[str, str] | None:
    match = _GITHUB_REPO_URL_RE.search(url)
    if not match:
        return None
    owner, repo = match.group(1), match.group(2)
    return owner, repo.removesuffix(".git")


def fetch_repo_metadata(url: str, session: Any | None = None) -> dict:
    """抓 GitHub repo 的客觀資安指標（star/最後commit/license/是否封存）。
    URL 無法解析、API 失敗、或網路錯誤一律回傳 {}，不中斷整體 ingest 流程（降級處理）。
    """
    parsed = parse_owner_repo(url)
    if parsed is None:
        return {}
    owner, repo = parsed

    headers = {"Accept": "application/vnd.github+json"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"

    requester = session or requests
    try:
        response = requester.get(
            f"https://api.github.com/repos/{owner}/{repo}", headers=headers, timeout=10
        )
    except requests.RequestException:
        return {}

    if response.status_code != 200:
        return {}

    data = response.json()
    license_info = data.get("license") or {}
    return {
        "repo_stars": data.get("stargazers_count"),
        "repo_last_push": data.get("pushed_at"),
        "repo_license": license_info.get("spdx_id"),
        "repo_archived": data.get("archived"),
    }
