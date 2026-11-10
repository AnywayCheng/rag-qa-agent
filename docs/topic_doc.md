# `topic.py` Technical Documentation

## 1. Technical Research
- **Similar Projects:** 意圖分類（intent classification）是常見的 NLU 任務，傳統做法會訓練專用分類模型；本專案改用「請 LLM 直接輸出結構化 JSON」的輕量做法，因為分類類別少（僅 news/paper/github 三種）且不需要極低延遲
- **Frameworks & Libraries:** `google-genai`（重用 `embeddings.get_client()`）
- **Communication Protocols:** HTTPS REST API（透過 `google-genai` SDK）
- **Data Format:** 要求模型輸出 JSON 字串，本模組用正規表示式從回應文字中擷取 `{...}` 區塊後以 `json.loads` 解析（Gemini API 沒有像 Anthropic 的 `output_config.format` 結構化輸出參數可用，因此用 prompt 引導 + 容錯解析的方式達成類似效果）
- **Authentication & Rate Limits:** 需要 `GEMINI_API_KEY`；每次 `normalize()` 呼叫消耗一次 Gemini 文字生成額度
- **Security Risks:** 模型輸出的 JSON 若格式不正確或內容不合法，一律降級為保守預設值（三面向都查），不會讓格式錯誤的輸出污染後續流程
- **Legal & Compliance:** 不適用
- **Deployment Environment:** 本地執行

## 2. Algorithmic Analysis
- **Algorithms Used:** (1) 正規表示式擷取回應文字中的 JSON 區塊（容忍模型把 JSON 包在 ```` ```json ```` code fence 或其他說明文字裡）；(2) 白名單過濾：只保留 `categories` 中屬於 `{"news","paper","github"}` 的項目，其餘視為模型幻覺產生的無效分類直接丟棄；(3) `slugify`：正規化字串為底線分隔的小寫標籤，用正規表示式移除標點符號，但保留中日韓統一表意文字（`一-鿿`）範圍的字元，讓中文主題也能保留可讀性
- **Time Complexity:** $O(L)$，$L$ 為回應文字長度（正規表示式掃描與 JSON 解析皆與文字長度成正比）
- **Space Complexity:** $O(L)$

## 3. Module & Dependency Map
- **Internal Dependencies:** `config`（`GENERATION_MODEL`）、`embeddings`（重用 `get_client()`）
- **External Dependencies:** `google-genai`；標準函式庫 `json`、`re`
- **Exposed Interface:**
  - `VALID_CATEGORIES: set[str]`：合法的三個面向
  - `normalize(question: str, client=None) -> dict`：問句 → `{topic_key, categories}`
  - `slugify(text: str) -> str`：字串正規化為 topic_key 格式（也被 `cli.py` 的 `refresh` 指令重用）

## 4. Key Design Decisions
- **Architecture Pattern:** 「LLM 輸出 + 容錯解析」模式，把不可靠的自然語言生成結果，透過嚴格的後處理（JSON 解析失敗檢查、欄位型別檢查、白名單過濾）收斂成可預期的結構化資料
- **Error Handling Strategy:** 三層降級保護：(1) 回應中找不到 `{...}` 區塊 → 降級；(2) 找到但 JSON 解析失敗（`json.JSONDecodeError`）→ 降級；(3) 解析成功但 `topic_key` 是空字串、或 `categories` 過濾後變成空清單 → 降級。降級策略統一是「把整個問句本身 slugify 當 topic_key，三個面向都查」，這是最保守但不會漏資訊的預設值
- **Concurrency Model:** 同步、單執行緒

## 5. Known Limitations & Future Work
- **Current Limitations:** 沒有對模型輸出做 retry（萬一這次剛好解析失敗，就直接用保守預設值，不會重問模型一次）；`slugify` 是簡單的正規表示式規則，無法保證語意相近但措辭不同的問題一定產生相同 `topic_key`（例如「AI新聞」vs「人工智慧新聞」不會被視為同一主題）
- **Suggested Improvements:** 若之後發現 topic_key 對不上導致誤判是新主題的情況頻繁發生，可以考慮改用 embedding 相似度比對既有 topic_key，而非純字串正規化
