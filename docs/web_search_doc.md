# `web_search.py` Technical Documentation

## 1. Technical Research
- **Similar Projects:** SerpAPI、Tavily、Bing Search API 都是類似的第三方搜尋整合方案；本專案改用 Gemini API 內建的 `google_search` grounding 工具，不用另外申請/串接第三方搜尋服務
- **Frameworks & Libraries:** `google-genai`（`client.interactions.create` + `tools=[{"type": "google_search"}]`）
- **Communication Protocols:** HTTPS REST API（透過 `google-genai` SDK）
- **Data Format:** 輸出為模型生成文字，佐證來源以 `url_citation` annotation 形式附加在文字片段上（含 `start_index`/`end_index`/`url`/`title`）
- **Authentication & Rate Limits:** 需要 `GEMINI_API_KEY`；免費額度：Flash 系列模型每天 500 次 grounding 搜尋（依 Gemini 定價頁，2026-09-22 查證）
- **Security Risks:** Google Search grounding 不支援 domain 白名單/黑名單參數，只能靠 prompt 文字引導範圍（例如 `site:github.com`），代表搜尋結果**不保證**真的只落在該網域——這是本模組防捏造規則存在的原因之一，不能無條件信任回傳內容
- **Legal & Compliance:** 需遵守 Google Gemini API 使用條款；搜尋結果引用第三方網站內容需注意著作權（本模組只存原文片段＋來源連結，不做額外改寫）
- **Deployment Environment:** 本地執行，對外發送 HTTPS 請求

## 2. Algorithmic Analysis
- **Algorithms Used:** (1) 依 `category` 選對應的 prompt 模板做字串格式化；(2) 遍歷 `interaction.steps` → `content` → `annotations` 的巢狀結構，過濾出 `type == "url_citation"` 的片段，並用 `start_index`/`end_index` 對原文字做 slice 取出確切被引用的文字（**防捏造核心邏輯**：沒有 annotation 的文字一律不收）
- **Time Complexity:** $O(S \cdot B \cdot A)$，$S$ 為 steps 數、$B$ 為每個 step 的 content block 數、$A$ 為每個 block 的 annotation 數；實務上這三個數字都很小（通常 $S,B,A \le 10$），可視為近似常數時間
- **Space Complexity:** $O(L)$，$L$ 為回應文字總長度

## 3. Module & Dependency Map
- **Internal Dependencies:** `config`（`GENERATION_MODEL`）、`embeddings`（重用其 `get_client()` 作為 genai client 工廠，因為兩者都需要同一種 `genai.Client`）
- **External Dependencies:** `google-genai`
- **Exposed Interface:**
  - `CATEGORY_PROMPTS: dict[str, str]`：news/paper/github 三面向的 prompt 模板
  - `search_category(topic, category, client=None) -> list[dict]`：對指定面向執行 grounding 搜尋，只回傳有 citation 佐證的片段（`text`/`source_url`/`source_title`）

## 4. Key Design Decisions
- **Architecture Pattern:** 策略模式的簡化版——`CATEGORY_PROMPTS` 是一個查表，依 `category` 選擇不同搜尋策略（prompt 模板），而非寫三個幾乎重複的函式
- **Error Handling Strategy:** 未知的 `category` 直接拋 `ValueError`（呼叫端應該只會傳入 `topic.normalize()` 篩選過的合法值，這裡是防禦性檢查）；解析回應時大量使用 `getattr(obj, attr, None) or []` 的寫法，避免 SDK 回應物件缺少某個屬性時直接拋 `AttributeError`，讓「這個 step/block 沒有我要的東西」自然被當成「跳過」而非「整個函式崩潰」
- **Concurrency Model:** 同步、單執行緒，三個面向若都要搜尋則由呼叫端（`agent.py`）依序各呼叫一次

## 5. Known Limitations & Future Work
- **Current Limitations:** 沒有針對「模型沒有使用 google_search 工具」的情況做特別判斷（純粹看有沒有 citation，沒有就是沒有結果，不會去區分是模型沒搜尋還是搜尋了但沒找到東西）；`site:xxx.com` 這種 prompt 引導方式不保證 100% 生效，Google 可能還是回傳不完全符合網域限制的結果
- **Suggested Improvements:** 未來若 Gemini API 開放 domain 限制參數，應優先改用官方參數而非 prompt 引導；可以加入對回傳來源網域的後處理過濾，進一步確保 `github` 面向真的只收 `github.com` 的結果
