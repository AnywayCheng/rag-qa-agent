# `config.py` Technical Documentation

## 1. Technical Research
- **Similar Projects:** 常見做法是用 `pydantic-settings`（Pydantic BaseSettings）做型別驗證的設定管理，本專案為求簡單直接用 `python-dotenv` + `os.getenv`，因為設定項不多，過度設計沒必要
- **Frameworks & Libraries:** `python-dotenv`（讀取 `.env` 檔案到環境變數）
- **Communication Protocols:** 不適用
- **Data Format:** `.env` 純文字 KEY=VALUE 格式
- **Authentication & Rate Limits:** 持有 `GEMINI_API_KEY`、`GITHUB_TOKEN` 這兩個敏感憑證，僅在記憶體中保存，不寫入 log
- **Security Risks:** `.env` 檔案含真實金鑰，已在 `.gitignore` 排除，避免意外 commit 洩漏；程式本身不會把金鑰印到 stdout
- **Legal & Compliance:** 不適用
- **Deployment Environment:** 本地執行，模組載入時即讀取一次環境變數（模組層級執行 `load_dotenv()`）

## 2. Algorithmic Analysis
- **Algorithms Used:** 無演算法邏輯，純設定值讀取與常數定義
- **Time Complexity:** $O(1)$，模組載入時執行一次固定數量的環境變數讀取
- **Space Complexity:** $O(1)$，固定數量的設定變數

## 3. Module & Dependency Map
- **Internal Dependencies:** 無（是最底層模組，被其他所有模組依賴，自己不依賴任何專案內模組）
- **External Dependencies:** `python-dotenv`（載入 `.env`）、`pathlib.Path`（標準函式庫，計算專案根目錄路徑）
- **Exposed Interface:** 模組層級常數：`GEMINI_API_KEY`、`GITHUB_TOKEN`、`FRESHNESS_TTL_HOURS`、`GENERATION_MODEL`、`EMBEDDING_MODEL`、`CHROMA_DB_PATH`、`CHROMA_COLLECTION_NAME`、`CHUNK_SIZE`、`CHUNK_OVERLAP`、`RETRIEVAL_TOP_K`

## 4. Key Design Decisions
- **Architecture Pattern:** 集中式設定模組（configuration module pattern），所有其他模組統一從這裡讀取設定，避免設定值散落各處
- **Error Handling Strategy:** 所有 `os.getenv` 呼叫都提供預設值，缺少 `.env` 檔案或個別變數時不會拋錯，而是靜默使用預設值（例如 `FRESHNESS_TTL_HOURS` 預設 24 小時）；唯一例外是 `GEMINI_API_KEY` 空字串時不會在這裡報錯，而是等到實際呼叫 Gemini API 時才會因認證失敗而報錯——這是刻意的，因為 `config.py` 本身不該知道「什麼時候一定要有 API Key」（例如跑純本地文件的單元測試就不需要）
- **Concurrency Model:** 不適用，模組層級常數，載入後不可變

## 5. Known Limitations & Future Work
- **Current Limitations:** 沒有對讀進來的值做型別/格式驗證（例如 `FRESHNESS_TTL_HOURS` 若 `.env` 填了非數字字串會在這裡直接拋 `ValueError`，而不是給出更友善的錯誤訊息）
- **Suggested Improvements:** 專案規模變大後可考慮改用 `pydantic-settings`，取得自動型別驗證、更清楚的錯誤訊息、以及巢狀設定支援
