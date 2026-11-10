# `agent.py` Technical Documentation

## 1. Technical Research
- **Similar Projects:** 概念上類似「self-updating RAG」或「web-augmented RAG with cache invalidation」，是 GraphRAG／傳統靜態 RAG 之外的第三種模式：用 TTL-based cache 語意管理「該不該重新查詢外部世界」，這是快取失效（cache invalidation）這個經典 CS 難題在 RAG 場景的具體應用
- **Frameworks & Libraries:** 無新增依賴，純粹是本專案內其他模組的 orchestration 層
- **Communication Protocols:** 不直接對外通訊，透過呼叫 `web_search`/`generator`/`topic` 間接觸發 HTTPS 請求
- **Data Format:** 內部資料流：問句字串 → `{topic_key, categories}` → 逐 category 的新鮮度判斷 → chunk 清單 → `{answer, sources, topic_key, categories, searched_categories}`
- **Authentication & Rate Limits:** 不適用於本模組本身（憑證管理在更底層的 `embeddings.py`/`config.py`）
- **Security Risks:** 本模組是整個「查新鮮度 → 決定搜尋 → 覆蓋寫入 → 生成回答」流程的守門員，所有防捏造/資安揭露規則能不能真正生效，取決於這裡的 orchestration 順序是否正確（例如：一定要先呼叫 `github_meta.fetch_repo_metadata` 把客觀指標塞進 `extra_metadata`，才呼叫 `ingest.overwrite_topic_category` 寫入，順序顛倒會導致 GitHub 客觀指標遺失）
- **Legal & Compliance:** 不適用
- **Deployment Environment:** 本地執行

## 2. Algorithmic Analysis
- **Algorithms Used:** (1) 新鮮度判斷 `_is_fresh`：計算 `fetched_at` 與現在時間的差距（小時），與可設定的 TTL 比較，是簡單的 cache-expiry 演算法；(2) 主流程 `ask()`：對每個相關 category 獨立跑「查新鮮度 → （過期則）搜尋+覆蓋 → 之後統一檢索」的迴圈，是一個小型的 orchestrator/coordinator 模式
- **Time Complexity:** $O(k \cdot (S + Q))$，$k$ 為問題涉及的 category 數量（最多 3）、$S$ 為單次網路搜尋的成本（含 embedding+API 呼叫）、$Q$ 為單次 Chroma 查詢成本；因為 $k \le 3$，整體可視為由單次搜尋/查詢成本主導
- **Space Complexity:** $O(k \cdot top\_k)$，暫存所有 category 的檢索結果於記憶體後才交給 `generator.generate_answer`

## 3. Module & Dependency Map
- **Internal Dependencies:** `config`（`FRESHNESS_TTL_HOURS`）、`generator`（生成最終回答）、`github_meta`（GitHub 客觀指標）、`ingest`（覆蓋寫入）、`retriever`（查詢/新鮮度）、`topic`（問句正規化）、`web_search`（三面向搜尋）——是整個 `rag_qa` 套件中依賴最多其他模組的一層，符合它作為 orchestration 層的定位
- **External Dependencies:** 標準函式庫 `datetime`
- **Exposed Interface:**
  - `ALL_CATEGORIES: list[str]`：三個合法面向（從 `web_search.CATEGORY_PROMPTS` 推導）
  - `ask(question, collection=None, client=None, force_refresh=False, categories=None) -> dict`：核心問答流程
  - `refresh_topic(topic_key, categories=None, collection=None, client=None) -> list[str]`：手動強制刷新（給 CLI `refresh` 指令用）

## 4. Key Design Decisions
- **Architecture Pattern:** Orchestrator / Coordinator 模式——這一層不包含任何「怎麼查詢」「怎麼生成」的實作細節，只負責決定「什麼時候該做什麼」，實作細節都委派給其他專職模組
- **Error Handling Strategy:** 刻意不在這層對下游模組的失敗做額外 try/except 包裝——`web_search.search_category` 找不到 citation 時回傳空清單（不是拋例外），`ingest.overwrite_topic_category` 對空 `facts` 清單的行為是「只刪不插」，這兩者組合起來自然達成「查無佐證資料時，RAG 該主題面向會被清空而不是留著舊資料」的正確行為，不需要在 `agent.py` 額外寫防禦邏輯
- **Concurrency Model:** 同步、單執行緒；`ask()` 中對多個 category 的搜尋是依序執行（非平行），因為 Gemini free tier 的 rate limit 考量下，平行呼叫的必要性不高，循序執行邏輯也更單純好懂

## 5. Known Limitations & Future Work
- **Current Limitations:** 多個 category 都需要搜尋時是依序執行，總延遲等於各面向延遲總和，使用者體感等待時間較長；`ask()` 最終檢索階段用同一個 `question` 對每個 category 分別查詢，沒有針對不同 category 調整 `top_k`（例如 github 面向可能不需要 5 筆）
- **Suggested Improvements:** 多 category 搜尋可改成並行（`asyncio` 或 `concurrent.futures`）縮短延遲；未來若要支援「每天定時自動掃描追蹤主題」的日常助手功能，`refresh_topic` 已經是現成的可重用進入點，只需要加一層排程觸發（見 README Future Work）
