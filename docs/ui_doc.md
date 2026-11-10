# `ui.py` Technical Documentation

## 1. Technical Research
- **Similar Projects:** Streamlit、Chainlit、Open WebUI 都是類似定位的 LLM app 快速建 UI 框架；本專案選 Gradio，因為 `ChatInterface` 元件天生對應「問答+來源」互動模型，且 Hugging Face Spaces 生態對 Gradio 部署支援最好，適合履歷專案做公開展示
- **Frameworks & Libraries:** `gradio`（6.28.0，底層用 FastAPI + Starlette 起本地網頁伺服器）
- **Communication Protocols:** HTTP（Gradio 內建 FastAPI 伺服器，預設監聽 `127.0.0.1:7860`），前端與後端之間用 Gradio 自己的元件事件機制溝通（點擊按鈕→呼叫 Python callback→更新畫面）
- **Data Format:** 檔案上傳元件（`gr.File`）以 `type="filepath"` 回傳本地暫存檔案路徑字串清單；聊天訊息為純文字字串
- **Authentication & Rate Limits:** 本模組不含身份驗證（預設只監聽本機，僅供個人使用）；底層呼叫的 Gemini/GitHub API 額度限制屬於 `agent.py`/`web_search.py`/`github_meta.py` 範疇
- **Security Risks:** `demo.launch()` 預設只監聽 localhost，不對外網開放，風險低；若之後要用 `share=True` 產生公開連結需注意任何人都能連進來操作（含觸發真實 API 呼叫，消耗你的額度）
- **Legal & Compliance:** 不適用
- **Deployment Environment:** 本地執行（`uv run rag-qa-ui`），未來可選擇性部署到 Hugging Face Spaces（見 README Future Work）

## 2. Algorithmic Analysis
- **Algorithms Used:** 無自訂演算法，純粹是既有後端函式（`agent.ask`/`agent.refresh_topic`/`ingest.ingest_local_file`）的介面包裝與結果格式化（字串拼接組 markdown）
- **Time Complexity:** $O(1)$ 就本模組邏輯本身而言（`format_answer` 對 `sources` 清單做一次線性遍歷，是 $O(k)$，$k$ 為來源數量，通常很小）；實際延遲取決於底層 `agent.ask` 等函式的網路呼叫
- **Space Complexity:** $O(1)$（本模組不額外持有大型狀態，Chroma 資料狀態委由 `retriever.get_collection()` 的模組層級單例管理）

## 3. Module & Dependency Map
- **Internal Dependencies:** `agent`（`ask`、`refresh_topic`）、`ingest`（`ingest_local_file`）、`topic`（`slugify`）——三個 handler 分別對應既有 CLI 三個指令背後呼叫的同一組函式，介面完全重用，沒有另外實作一套邏輯
- **External Dependencies:** `gradio`
- **Exposed Interface:**
  - `format_answer(result: dict) -> str`：把 `agent.ask()` 回傳結果格式化成聊天訊息
  - `chat_fn(message: str, history: list) -> str`：`ChatInterface` 的 callback
  - `handle_ingest_files(file_paths, collection=None) -> str`：匯入分頁的按鈕 callback
  - `handle_refresh(topic_text, categories, collection=None, client=None) -> str`：刷新分頁的按鈕 callback
  - `build_app() -> gr.Blocks`：組出完整介面（測試不覆蓋這個函式本身，見下方）
  - `main() -> None`：`rag-qa-ui` console script 進入點

## 4. Key Design Decisions
- **Architecture Pattern:** 「邏輯與框架接線分離」——三個 handler 都寫成純函式（輸入輸出明確、可注入 `collection`/`client` 依賴），`build_app()` 只負責把這些純函式接到 Gradio 元件上，不含任何業務邏輯。這讓單元測試能完全避開 Gradio 框架本身（測試跑得快、不需要真的啟動網頁伺服器），只有 `build_app()`/`main()` 這層「接線」沒有自動化測試，改用手動跑一次 `uv run rag-qa-ui` 在瀏覽器驗證（golden path + 至少一個邊界情況）
- **Error Handling Strategy:** 三個 handler 最外層統一包 `try/except Exception`，把任何例外（API Key 沒設定、網路逾時、embedding 失敗等）轉成一句友善中文訊息顯示在介面上，而不是讓 Gradio 顯示原始 traceback 或整個頁面报錯——這是 UI 邊界該做的防禦（使用者看不懂 Python traceback），不是「防禦不會發生的情況」，因為外部 API 呼叫失敗是真實會發生的情境（已在手動測試中實際驗證：`GEMINI_API_KEY` 未設定時確實顯示「發生錯誤：No API key was provided...」而非讓介面崩潰）
- **Concurrency Model:** Gradio 預設每個瀏覽器 session 獨立處理請求（底層 FastAPI 非同步），但本模組的 handler 本身是同步函式；因為 `agent.ask()` 等呼叫本身是阻塞式，多個使用者同時操作時後端會依 Gradio 的並行設定排隊處理，本專案未特別調整並行限制（單人本地使用情境，非必要）

## 5. Known Limitations & Future Work
- **Current Limitations:** `chat_fn` 沒有使用 `history` 參數，每次提問都是獨立的（不具備多輪對話上下文記憶，跟 `agent.ask()` 本身的設計一致）；`build_app()`/`main()` 沒有自動化測試覆蓋，仰賴手動驗證
- **Suggested Improvements:** 若要公開部署到 Hugging Face Spaces，需額外處理 `GEMINI_API_KEY` 的安全存放（用 Spaces 的 Secrets 機制，不能寫死在程式碼或 `.env` 一起上傳）；若要支援多輪對話，可以把 `history` 一併傳入 `agent.ask()`，但這會需要修改 `agent.py`/`generator.py` 支援對話歷史，屬於範疇外的變更
