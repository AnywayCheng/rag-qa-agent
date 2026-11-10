# `cli.py` Technical Documentation

## 1. Technical Research
- **Similar Projects:** Typer、Click 是常見的 Python CLI 框架；本專案改用標準函式庫 `argparse`，因為指令集簡單（三個子指令），不需要額外依賴，也避免依賴專案裡其他套件（如 chromadb）間接帶入的 `typer` transitive dependency（那個不受本專案直接控管，未來可能隨套件升級消失）
- **Frameworks & Libraries:** 標準函式庫 `argparse`
- **Communication Protocols:** 不適用（終端機 stdin/stdout 互動）
- **Data Format:** 命令列參數（字串）；輸出為終端機文字
- **Authentication & Rate Limits:** 不適用於本模組本身
- **Security Risks:** 無使用者輸入會被拿去執行 shell 指令或寫入檔案系統之外的操作，風險低
- **Legal & Compliance:** 不適用
- **Deployment Environment:** 本地終端機執行，透過 `pyproject.toml` 的 `[project.scripts]` 註冊為 `rag-qa` 可執行指令（`uv run rag-qa ...`）

## 2. Algorithmic Analysis
- **Algorithms Used:** 無演算法邏輯，純粹是參數解析與函式呼叫的路由分派（dispatch），對應到 `argparse` 的 subcommand 機制
- **Time Complexity:** $O(1)$（就 CLI 層本身而言，實際耗時取決於底層呼叫的 `agent.ask`/`ingest.ingest_directory` 等函式）
- **Space Complexity:** $O(1)$

## 3. Module & Dependency Map
- **Internal Dependencies:** `agent`（`ask`、`refresh_topic`）、`ingest`（`ingest_directory`）、`topic`（`slugify`，把使用者輸入的自然語言主題正規化成 topic_key）
- **External Dependencies:** 標準函式庫 `argparse`、`sys`、`pathlib.Path`
- **Exposed Interface:**
  - `build_parser() -> argparse.ArgumentParser`：建立三個子指令（`ingest`/`ask`/`refresh`）的 parser，回傳值可在測試中直接呼叫 `parse_args()` 而不執行 `main()`，方便測試
  - `main() -> None`：程式進入點（`pyproject.toml` 的 `rag-qa` script 指向這裡）

## 4. Key Design Decisions
- **Architecture Pattern:** 標準的 argparse subcommand 模式，每個子指令對應一個 `_cmd_*` handler 函式，透過 `set_defaults(func=...)` 綁定，`main()` 統一呼叫 `args.func(args)`
- **Error Handling Strategy:** `ingest` 指令遇到不存在的目錄時印出錯誤訊息到 `stderr` 並回傳 exit code 1（讓 shell script 可以判斷成功/失敗）；`main()` 額外處理 Windows 主控台編碼問題——偵測到 `stdout.encoding` 不是 UTF-8 時強制 `reconfigure`，避免繁體中文輸出在部分 Windows 終端機（例如傳統 cmd.exe 非 UTF-8 codepage）顯示亂碼
- **Concurrency Model:** 同步、單執行緒；CLI 呼叫本身是阻塞式（等待 `agent.ask()` 完成才印出結果）

## 5. Known Limitations & Future Work
- **Current Limitations:** 沒有互動模式（每次都要重新打完整指令，無法像 REPL 一樣連續問答）；`refresh` 指令目前只接受單一主題文字，無法一次刷新多個追蹤主題
- **Suggested Improvements:** 加入互動式 REPL 模式（`rag-qa chat`），方便連續問答不用每次重打指令；若之後要做「每天上班先掃一輪」的日常助手功能，可以在這裡加一個 `rag-qa daily-refresh --topics-file topics.json` 之類的批次指令，讀取追蹤主題清單逐一呼叫 `refresh_topic`
