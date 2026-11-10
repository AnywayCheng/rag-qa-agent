# `embeddings.py` Technical Documentation

## 1. Technical Research
- **Similar Projects:** OpenAI Embeddings API、Cohere Embed、sentence-transformers（本地開源方案）都是類似的文字向量化服務；本專案選 Google Gemini 的 `gemini-embedding-001`，因為有免費額度且跟生成模型同一套 SDK
- **Frameworks & Libraries:** `google-genai`（Google 官方 SDK，`from google import genai`）
- **Communication Protocols:** HTTPS REST API（由 `google-genai` SDK 封裝，呼叫端看不到底層 HTTP 細節）
- **Data Format:** 輸入為純文字字串或字串清單；輸出為浮點數向量（`list[float]`）或向量清單
- **Authentication & Rate Limits:** 需要 `GEMINI_API_KEY`（透過 `config.GEMINI_API_KEY` 注入）；免費額度依 Google 定價頁規定（Embedding 系列在免費層內）
- **Security Risks:** API Key 僅存在記憶體中，不寫入 log 或錯誤訊息；傳給第三方（Google）的內容是使用者問句與文件片段，需注意不要 embedding 敏感個資
- **Legal & Compliance:** 需遵守 Google Gemini API 使用條款
- **Deployment Environment:** 本地執行，對外發送 HTTPS 請求到 Google 伺服器

## 2. Algorithmic Analysis
- **Algorithms Used:** 無自訂演算法，直接委派給 Gemini embedding 模型（底層為 transformer-based embedding model，對呼叫端是黑盒）；本模組的邏輯僅是「依 query/document 用途組不同的 `task_type` 參數」，這是 retrieval 系統的標準作法：query 與 document 用不同 task_type 編碼，能讓兩者在向量空間中更容易配對
- **Time Complexity:** $O(1)$（就函式本身邏輯而言；實際延遲取決於網路請求跟 Gemini 伺服器端運算，不計入這裡）
- **Space Complexity:** $O(k)$，$k$ 為輸入文字數量乘上向量維度（`gemini-embedding-001` 預設輸出維度）

## 3. Module & Dependency Map
- **Internal Dependencies:** `config`（讀取 `GEMINI_API_KEY`、`EMBEDDING_MODEL`）
- **External Dependencies:** `google-genai`（`genai.Client`、`genai.types.EmbedContentConfig`）
- **Exposed Interface:**
  - `get_client() -> genai.Client`：取得（或延遲建立、快取）genai client 單例
  - `embed_query(text: str, client=None) -> list[float]`：問句 embedding，`task_type="RETRIEVAL_QUERY"`
  - `embed_documents(texts: list[str], client=None) -> list[list[float]]`：文件 chunk 批次 embedding，`task_type="RETRIEVAL_DOCUMENT"`，保留輸入順序

## 4. Key Design Decisions
- **Architecture Pattern:** 依賴注入（dependency injection）——所有函式都接受可選的 `client` 參數，預設用模組層級單例，測試時可以注入 mock client，不需要真的打 API 就能驗證邏輯
- **Error Handling Strategy:** 目前不做特別的重試或錯誤包裝，讓 `google-genai` SDK 的例外直接往上拋（呼叫端如 `ingest.py`/`agent.py` 目前也還沒針對 embedding API 失敗做特別處理——這是已知限制，見下方）；唯一的邊界防護是 `embed_documents([])` 直接回傳空清單，不浪費一次 API 呼叫
- **Concurrency Model:** 同步呼叫，未使用 async/並行批次

## 5. Known Limitations & Future Work
- **Current Limitations:** 沒有針對 rate limit（429）或暫時性網路錯誤做重試機制；`embed_documents` 沒有依 API 單次請求上限自動分批（若一次傳入超大量文字可能超過 API 限制而直接失敗）
- **Suggested Improvements:** 加入指數退避重試（exponential backoff）處理暫時性錯誤；當 `texts` 數量很大時自動切批次呼叫
