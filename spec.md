# spec.md — RAG 知識庫問答系統（含網路搜尋保鮮）

## 目標

一個會自動判斷知識是否過期、過期就上網搜尋補新資料的問答 Agent。支援兩種資料來源：

1. **本地文件**（PDF / txt / md）：使用者手動 `ingest`，內容不會過期、不會被覆蓋
2. **網路搜尋**（news / paper / github 三面向）：問問題時 Agent 自動判斷是否需要重新搜尋，過期就覆蓋舊資料

## 輸入格式

- 本地文件：`.pdf`、`.txt`、`.md`，放在 `data/raw/`
- 使用者問題：任意中/英文自然語言問句

## Chunking 策略（僅本地文件路徑）

- 固定長度切分：500 字 / chunk，overlap 50 字
- 邊界情況：空文件跳過並記錄警告；文件長度小於 500 字整份當一個 chunk

## 檢索

- 向量相似度 top-k，預設 `k=5`
- 網路來源查詢可依 `category`（news/paper/github）過濾

## 核心設計規則

### 1. 防捏造（Anti-hallucination）

存進 RAG 的**網路搜尋**內容，必須對應 Gemini grounding 回應中的 `url_citation` annotation（有明確來源網址）。沒有 citation 佐證的文字一律丟棄，不寫入 Chroma。若某次搜尋完全沒有 citation，回答時明講「這個面向目前查無佐證資料」，不得由模型憑空生成內容替代。

（本地文件路徑不受此規則限制——文件內容本身就是佐證來源。）

### 2. 三面向網路搜尋

一個查詢主題最多觸發三種獨立搜尋：

| category | 用途 | 搜尋 prompt 模板 |
|---|---|---|
| `news` | 新聞資訊 | 搜尋關於「{topic}」的最新新聞報導 |
| `paper` | 論文期刊 | 搜尋關於「{topic}」的最新學術論文/期刊研究，優先 `site:arxiv.org OR site:pubmed.ncbi.nlm.nih.gov OR site:scholar.google.com` |
| `github` | 開源工具/skill | 搜尋 GitHub 上關於「{topic}」的最新工具/repository/skill，`site:github.com` |

每個面向各自呼叫一次 `google_search` grounding（Gemini API 不支援 domain 限制參數，只能在 prompt 文字裡引導）。

### 3. GitHub 資安揭露

LLM 無法真的稽核程式碼安全性，一律改用客觀指標：每個 GitHub 搜尋結果額外呼叫 GitHub 公開 REST API（`https://api.github.com/repos/{owner}/{repo}`）取得：

- `stargazers_count`（star 數）
- `pushed_at`（最後 commit 時間）
- `license`
- `archived`（是否已封存）

生成回答時，`github` 類別內容必須附上這些客觀數據，以及固定免責提醒：

> 「以上工具未經本系統資安審查，是否安裝／使用請自行評估來源可信度。」

模型**不得**自行生成「這個安全」之類的背書文字。GitHub API 抓取失敗（rate limit / repo 不存在）時降級處理：內容照樣存入，缺少的欄位留空，不中斷整體流程。

### 4. Non-goal：不自動執行

系統只做資訊蒐集與呈現。**絕不**自動下載、clone、安裝或執行任何搜尋到的程式碼或工具。所有找到的 GitHub 工具都只是「建議參考」，安裝與否由使用者自行判斷。

### 5. 覆蓋與新鮮度

- 覆蓋比對單位：`topic_key` + `category` 組合
- 每筆網路來源資料帶 `fetched_at`（ISO8601），超過 `FRESHNESS_TTL_HOURS`（預設 24 小時，`.env` 可調）視為過期
- 過期或不存在 → 觸發該 category 的搜尋 → 用 `topic_key`+`category` 篩選刪除舊資料 → 插入新資料
- 未過期 → 直接用既有資料回答，不重新搜尋
- 同一個問題可能同時觸發多個 category（例如「AI 最新資訊」預設涵蓋三個面向都要查），各 category 的新鮮度判斷互相獨立

## Topic 正規化

使用者問句 → 一次輕量 Gemini 呼叫 → `{topic_key: str, categories: list[str]}`

- `topic_key`：正規化後的主題標籤（讓不同措辭的同主題問題能對應到同一份資料，例如「生醫最新資訊」和「biomedical news」應正規化成同一個 key）
- `categories`：問題實際要問的面向；模糊問題（如「最新資訊」）預設三個面向都要

## Chroma Metadata Schema

| 欄位 | 說明 | 適用範圍 |
|---|---|---|
| `source` | `"web"` 或 `"local_file"` | 全部 |
| `topic_key` | 正規化主題標籤 | 僅 web |
| `category` | `news`/`paper`/`github`/`local_file` | 全部 |
| `fetched_at` | ISO8601 時間戳 | 僅 web |
| `source_url` | 佐證來源網址 | 僅 web |
| `source_title` | 來源標題 | 僅 web |
| `repo_stars` / `repo_last_push` / `repo_license` / `repo_archived` | GitHub 客觀指標 | 僅 `category=="github"` |

## Non-goals（這次不做）

- 每日定時自動掃描追蹤主題（排程自動化）——留 Future Work
- GraphRAG（跨文件實體關係）——成本/複雜度不符合現階段資源限制
- 保留歷史版本——會拖累檢索準確率，明確採用完全覆蓋策略
