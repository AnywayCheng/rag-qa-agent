# `generator.py` Technical Documentation

## 1. Technical Research
- **Similar Projects:** 這是典型的 RAG「生成」階段，概念上等同 LangChain 的 `RetrievalQA` chain 或 LlamaIndex 的 `ResponseSynthesizer`；本專案手刻 prompt 組裝邏輯，直接控制 context 格式與安全規則的落地方式
- **Frameworks & Libraries:** `google-genai`（重用 `embeddings.get_client()`）
- **Communication Protocols:** HTTPS REST API（透過 `google-genai` SDK）
- **Data Format:** 輸入為檢索到的 chunk 清單（`document`+`metadata`），輸出為 `{answer: str, sources: list[dict]}`
- **Authentication & Rate Limits:** 需要 `GEMINI_API_KEY`
- **Security Risks:** 這是防捏造與資安揭露規則最終落地的一層——prompt 明確要求模型不能編造參考資料以外的內容、不能對 GitHub 工具做安全背書；同時程式碼層面用確定性邏輯（非依賴模型是否乖乖聽話）強制在含 GitHub 內容的回答加上免責提醒（`GITHUB_DISCLAIMER`），這是防禦深度（defense in depth）的實踐：不能只靠 prompt instruction，因為 LLM 不保證 100% 遵從
- **Legal & Compliance:** 不適用
- **Deployment Environment:** 本地執行

## 2. Algorithmic Analysis
- **Algorithms Used:** (1) Context 組裝：把檢索結果格式化成帶編號的 `[來源N]` 區塊，GitHub 類別額外附加客觀指標字串；(2) 確定性後處理：檢查回答文字是否已含免責提醒字串，沒有就強制附加（字串包含檢查 + 條件式拼接，非 LLM 決策）
- **Time Complexity:** $O(C)$，$C$ 為傳入的 chunk 數量（context 組裝為線性遍歷）；來源清單抽取同樣是 $O(C)$
- **Space Complexity:** $O(C \cdot L)$，$L$ 為平均每個 chunk 的文字長度

## 3. Module & Dependency Map
- **Internal Dependencies:** `config`（`GENERATION_MODEL`）、`embeddings`（重用 `get_client()`）
- **External Dependencies:** `google-genai`
- **Exposed Interface:**
  - `GITHUB_DISCLAIMER: str`：固定資安免責提醒文字（模組層級常數，供測試與其他模組比對）
  - `generate_answer(question: str, chunks: list[dict], client=None) -> dict`：組 prompt 並生成回答，回傳 `{answer, sources}`

## 4. Key Design Decisions
- **Architecture Pattern:** Template method 的簡化版——固定的 `_ANSWER_PROMPT` 模板搭配動態組裝的 context 區塊
- **Error Handling Strategy:** `chunks` 為空清單時直接回傳固定訊息「目前查無相關資料可以回答這個問題」，**不呼叫 API**（省成本，也避免模型在完全沒有 context 時亂猜）；GitHub 免責提醒用「先檢查是否已存在，不存在才附加」的邏輯避免重複附加兩次
- **Concurrency Model:** 同步、單執行緒

## 5. Known Limitations & Future Work
- **Current Limitations:** 沒有限制傳入 `chunks` 的總長度，若上游（`agent.py`）一次塞入過多 chunk（例如三個面向都各抓 5 筆＋本地文件 5 筆＝20 筆），prompt 可能變得很長，增加成本與延遲；來源清單（`sources`）目前沒有去重，同一個 URL 若被多個 chunk 引用會重複出現
- **Suggested Improvements:** 加入 `sources` 去重邏輯（依 `source_url` unique）；若 context 過長可加入依 `distance`（相似度）排序後只取最相關的前 N 筆
