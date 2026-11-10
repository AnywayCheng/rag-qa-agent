# `retriever.py` Technical Documentation

## 1. Technical Research
- **Similar Projects:** Pinecone、Weaviate、Qdrant、FAISS 都是類似的向量檢索方案；本專案選 Chroma 因為零額外服務、本地檔案持久化，適合這台硬體資源有限的開發機
- **Frameworks & Libraries:** `chromadb`（`chromadb.PersistentClient`）
- **Communication Protocols:** 本地檔案系統存取（Chroma persistent client 用本地 SQLite/Parquet 混合儲存，不經過網路）
- **Data Format:** 向量（`list[float]`）+ 文件文字（`str`）+ metadata（`dict`，值限定 str/int/float/bool）
- **Authentication & Rate Limits:** 不適用（本地資料庫，無認證機制）
- **Security Risks:** `chroma_db/` 目錄含所有已搜尋/匯入的內容，若機器多人共用需注意存取權限；已加入 `.gitignore` 避免資料被誤 commit
- **Legal & Compliance:** 不適用
- **Deployment Environment:** 本地執行，資料庫檔案存在專案目錄下的 `chroma_db/`

## 2. Algorithmic Analysis
- **Algorithms Used:** 向量相似度最近鄰搜尋（Chroma 底層預設用 HNSW，Hierarchical Navigable Small World graph，近似最近鄰演算法）；`latest_fetched_at` 則是線性掃描符合條件的 metadata 取最大值（ISO8601 字串可直接字典序比較，等同時間排序）
- **Time Complexity:** HNSW 查詢約為 $O(\log N)$（$N$ 為向量總數，近似值，實際效能依索引參數而定）；`latest_fetched_at` 的線性掃描是 $O(m)$，$m$ 為符合 `topic_key`+`category` 條件的筆數（通常很小，因為同一組合的資料在覆蓋機制下只會有一批）
- **Space Complexity:** $O(N \cdot d)$，$N$ 為儲存的向量總數，$d$ 為向量維度（HNSW 索引本身也需要額外空間存圖結構）

## 3. Module & Dependency Map
- **Internal Dependencies:** `config`（`CHROMA_DB_PATH`、`CHROMA_COLLECTION_NAME`、`RETRIEVAL_TOP_K`）、`embeddings`（`embed_query`，把問句轉成查詢向量）
- **External Dependencies:** `chromadb`
- **Exposed Interface:**
  - `topic_category_filter(topic_key, category) -> dict`：組出 Chroma `$and` where 條件，給 `ingest.py` 覆蓋邏輯共用
  - `get_collection() -> Collection`：取得（或建立）persistent Chroma collection 單例
  - `query(query_text, top_k=5, category=None, collection=None) -> list[dict]`：向量相似度查詢，回傳含 `document`/`metadata`/`distance` 的結果清單
  - `latest_fetched_at(topic_key, category, collection=None) -> str | None`：查某 topic+category 目前最新的 `fetched_at` 時間戳，給新鮮度判斷用

## 4. Key Design Decisions
- **Architecture Pattern:** Repository pattern 的簡化版——把所有跟 Chroma 底層 API 的互動集中在這個模組，其他模組（`ingest.py`/`agent.py`）不直接碰 Chroma client
- **Error Handling Strategy:** 目前假設 Chroma 操作不會失敗（本地檔案系統操作，失敗機率低），沒有額外的 try/except 包裝；`where` 條件用 `$and` 明確組合多欄位過濾，是實測 Chroma 1.5.9 API 後確認的正確語法（單一 `where` dict 若含多個 key 會直接被 Chroma 拒絕，需明確用 `$and`）
- **Concurrency Model:** 同步、單執行緒；`get_collection()` 用模組層級變數快取 client 單例，重複呼叫不會重新建立連線

## 5. Known Limitations & Future Work
- **Current Limitations:** `query()` 的 top_k 是固定值，沒有依 collection 實際資料量動態調整；`get_collection()` 的 client 快取是全域單例，測試時需要明確傳入獨立的 `collection` 參數才能隔離（已在測試中處理，但對未來多租戶/多資料庫情境不友善）
- **Suggested Improvements:** 若之後要比較 Chroma 與 FAISS 的效能差異（履歷加分項），可以在這層抽出共用介面，方便替換底層向量DB實作
