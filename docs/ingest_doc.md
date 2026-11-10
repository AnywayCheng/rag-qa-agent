# `ingest.py` Technical Documentation

## 1. Technical Research
- **Similar Projects:** LangChain 的 `DocumentLoader` + `VectorStore.add_documents()` 是類似功能的框架化實作；本專案手刻是為了展示對 ingest pipeline 每個步驟（讀檔→切塊→embedding→寫入）的掌控
- **Frameworks & Libraries:** `pypdf`（PDF 文字擷取）
- **Communication Protocols:** 本地檔案系統讀取（`pathlib.Path.read_text`、`PdfReader`）
- **Data Format:** 輸入為 `.pdf`/`.txt`/`.md` 檔案；輸出為 Chroma 向量+文字+metadata 三元組
- **Authentication & Rate Limits:** 不適用於本模組本身（embedding 呼叫的額度限制屬於 `embeddings.py`/Gemini API 範疇）
- **Security Risks:** PDF 解析函式庫本身存在過往已知的惡意 PDF 漏洞風險（`pypdf` 為維護中的社群分支，已修復多數已知問題），本專案僅處理使用者自己放入 `data/raw/` 的檔案，風險可控；未對檔案大小做上限檢查，極大檔案可能造成記憶體壓力
- **Legal & Compliance:** 使用者需自行確保匯入的文件內容有合法使用權限
- **Deployment Environment:** 本地執行

## 2. Algorithmic Analysis
- **Algorithms Used:** (1) 檔案格式分派（依副檔名選擇讀取方式）；(2) 委派 `chunking.chunk_text` 做固定長度切分；(3) 「先刪後插」覆蓋演算法（`overwrite_topic_category`）：用 `topic_key`+`category` 查出所有舊 id，`delete(ids=...)` 全部刪除後才 `upsert` 新資料，確保同主題同面向在任何時間點最多只有一批資料，實現需求中「完全覆蓋、不保留歷史」的規則
- **Time Complexity:** `ingest_local_file`：$O(N)$，$N$ 為文件長度（讀檔+切塊+embedding 皆與長度成正比）；`overwrite_topic_category`：$O(m + k)$，$m$ 為待刪除的舊資料筆數、$k$ 為新資料筆數
- **Space Complexity:** $O(N)$（暫存整份文件文字與其切出的所有 chunk 於記憶體）

## 3. Module & Dependency Map
- **Internal Dependencies:** `chunking`（切分文字）、`config`（`CHUNK_SIZE`/`CHUNK_OVERLAP`）、`embeddings`（`embed_documents`）、`retriever`（`get_collection`、`topic_category_filter`）
- **External Dependencies:** `pypdf`（PDF 解析）
- **Exposed Interface:**
  - `ingest_local_file(path, collection=None) -> int`：單一本地文件 ingest，回傳寫入的 chunk 數
  - `ingest_directory(directory, collection=None) -> dict[str, int]`：批次 ingest 目錄下所有支援格式文件
  - `overwrite_topic_category(topic_key, category, facts, collection=None) -> int`：網路搜尋結果覆蓋寫入，回傳寫入筆數

## 4. Key Design Decisions
- **Architecture Pattern:** Pipeline 模式（讀取 → 切分 → 向量化 → 儲存），每步驟對應一個可獨立測試的小函式
- **Error Handling Strategy:** 空文件（切分後 chunk 數為 0）直接回傳 0，不寫入 Chroma、不報錯；`overwrite_topic_category` 收到空的 `facts` 清單時，仍會執行「刪除舊資料」但不插入新資料，回傳 0——這對應防捏造規則：網路搜尋若沒找到任何有 citation 佐證的內容，寧可讓該主題在 RAG 裡「沒有資料」，也不留著可能過時或錯誤的舊資料誤導使用者；metadata 裡的 `None` 值會被主動過濾掉（Chroma metadata 不接受 `None`），避免寫入時直接報錯
- **Concurrency Model:** 同步、單執行緒，批次 ingest 逐檔案依序處理

## 5. Known Limitations & Future Work
- **Current Limitations:** `ingest_directory` 只掃描目錄第一層，不遞迴子目錄；PDF 若是掃描影像檔（無文字層）會抓不到任何文字，目前沒有 OCR 備援
- **Suggested Improvements:** 加入遞迴子目錄掃描選項；PDF 無文字層時可整合 OCR（例如 Tesseract）作為備援
