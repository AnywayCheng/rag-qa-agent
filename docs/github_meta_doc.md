# `github_meta.py` Technical Documentation

## 1. Technical Research
- **Similar Projects:** GitHub 官方的 `gh` CLI、Libraries.io、Snyk Advisor 都提供類似的套件健康度指標查詢；本模組只取最基本的客觀公開資訊（star/最後 commit/license/是否封存），不做深度資安掃描（例如不掃程式碼本身、不查已知 CVE），因為那超出本專案範疇
- **Frameworks & Libraries:** `requests`（HTTP client）
- **Communication Protocols:** HTTPS REST API（GitHub REST API v3，`https://api.github.com/repos/{owner}/{repo}`）
- **Data Format:** GitHub API 回傳 JSON，本模組只取其中 `stargazers_count`/`pushed_at`/`license.spdx_id`/`archived` 四個欄位
- **Authentication & Rate Limits:** 未認證請求每小時 60 次（GitHub 官方限制）；`.env` 可選填 `GITHUB_TOKEN`（Personal Access Token）提高額度，若設定會以 `Authorization: Bearer <token>` header 帶入
- **Security Risks:** 本模組**不會**執行、下載或 clone 任何找到的 repo，只讀取 repo metadata；這是刻意的架構邊界（見 spec.md non-goal），避免系統被誤用成自動安裝未經審查程式碼的管道
- **Legal & Compliance:** 需遵守 GitHub API 使用條款與 rate limit 規定
- **Deployment Environment:** 本地執行，對外發送 HTTPS 請求

## 2. Algorithmic Analysis
- **Algorithms Used:** (1) 用正規表示式從任意 GitHub URL（含 `/blob/`、`/tree/` 等子路徑，或 `.git` 結尾）解析出 `owner`/`repo`；(2) 打 API 取得 metadata，失敗時降級回傳空字典（不拋例外中斷呼叫端流程）
- **Time Complexity:** $O(1)$ 就函式邏輯本身而言（正規表示式匹配、單次 HTTP 請求皆視為常數時間操作，不含網路延遲）
- **Space Complexity:** $O(1)$，回傳固定數量的欄位

## 3. Module & Dependency Map
- **Internal Dependencies:** `config`（`GITHUB_TOKEN`）
- **External Dependencies:** `requests`
- **Exposed Interface:**
  - `parse_owner_repo(url: str) -> tuple[str, str] | None`：從 GitHub URL 解析 owner/repo
  - `fetch_repo_metadata(url: str, session=None) -> dict`：抓取 repo 客觀指標，失敗一律回傳 `{}`

## 4. Key Design Decisions
- **Architecture Pattern:** 「降級優先」設計（graceful degradation）——這是本模組最核心的設計哲學：URL 解析不出來、API 404、rate limit、網路逾時，全部統一處理成回傳 `{}`，讓 `ingest.py` 照樣把文字內容存進 RAG（只是缺少客觀指標欄位），而不是讓一個 GitHub API 問題拖垮整個 `agent.ask()` 流程
- **Error Handling Strategy:** 用 `try/except requests.RequestException` 捕捉所有網路層級錯誤（連線逾時、DNS 失敗等）；HTTP 狀態碼非 200（404 repo 不存在、403 rate limit 等）也視為失敗降級，不細分錯誤類型回傳給呼叫端——因為呼叫端（`agent.py`）不需要知道「為什麼」失敗，只需要知道「有沒有拿到資料」
- **Concurrency Model:** 同步、單執行緒；`session` 參數支援依賴注入，測試時可傳入 mock 物件

## 5. Known Limitations & Future Work
- **Current Limitations:** 未認證時每小時僅 60 次請求，若同一批搜尋結果裡有多個 GitHub repo，額度可能很快用完；沒有針對 403 rate limit 做退避重試，直接視為失敗
- **Suggested Improvements:** 加入請求頻率節流（throttling）避免短時間內打爆 rate limit；偵測到 403 + rate limit 相關 header 時可以更明確地記錄「這次是因為額度用完」而非泛用的失敗
