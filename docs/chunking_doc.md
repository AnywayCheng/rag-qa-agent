# `chunking.py` Technical Documentation

## 1. Technical Research
- **Similar Projects:** LangChain 的 `RecursiveCharacterTextSplitter`、LlamaIndex 的 `SentenceSplitter` 都是類似用途的套件，但都是遞迴/語意感知切分，本專案刻意選擇最簡單的固定長度＋overlap 切法，為了展示對 chunking 底層機制的理解，而非依賴框架黑盒
- **Frameworks & Libraries:** 純 Python 標準函式庫實作，不依賴任何第三方套件
- **Communication Protocols:** 不適用（純本地字串處理，無網路通訊）
- **Data Format:** 輸入輸出皆為純文字字串（`str`），無結構化格式
- **Authentication & Rate Limits:** 不適用
- **Security Risks:** 無外部輸入風險（純字串切分），但若上游沒有限制輸入文件大小，極長文字可能造成記憶體壓力；目前未做檔案大小上限檢查
- **Legal & Compliance:** 不適用
- **Deployment Environment:** 本地執行，作為 `ingest.py` 的內部依賴，不獨立部署

## 2. Algorithmic Analysis
- **Algorithms Used:** 滑動視窗（sliding window）固定長度切分。以 `stride = chunk_size - overlap` 為步進量，從字串頭開始依序切出長度為 `chunk_size` 的片段，讓相鄰片段之間有 `overlap` 字元重疊，避免語意在切點被硬生生截斷
- **Time Complexity:** $O(N)$，$N$ 為輸入文字長度。迴圈執行次數約為 $N / stride$，每次切片操作本身是 $O(chunk\_size)$（Python 字串 slice 為常數時間到線性時間視實作而定），整體仍與 $N$ 成正比
- **Space Complexity:** $O(N)$。輸出的所有 chunk 加總長度約為 $N + (chunk\_count - 1) \times overlap$，與輸入長度同數量級

## 3. Module & Dependency Map
- **Internal Dependencies:** 無（不 import 專案內其他模組）
- **External Dependencies:** 無（純標準函式庫）
- **Exposed Interface:** `chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]`：對外唯一函式，切分文字並回傳 chunk 清單

## 4. Key Design Decisions
- **Architecture Pattern:** 單一純函式（pure function），無副作用、無狀態，方便單元測試與重用
- **Error Handling Strategy:** 對不合理的參數（`overlap` 為負數或 `overlap >= chunk_size`）直接拋出 `ValueError`，讓呼叫端在設定階段就發現問題，而非產生無限迴圈或錯誤切分結果；空字串或純空白字串直接回傳空清單（視為無內容可切）
- **Concurrency Model:** 不適用，單執行緒同步函式

## 5. Known Limitations & Future Work
- **Current Limitations:** 純字元長度切分，不理解句子/段落邊界，可能把句子從中間切斷；不支援 token-based 切分（例如依 LLM tokenizer 計算長度），對於需要精確控制 prompt token 數的場景不夠精準
- **Suggested Improvements:** 之後可加入以句子/段落為邊界的語意切分（例如優先在句號、換行處斷開）；若要更貼近 LLM 實際消耗的 token 數，可改用 tokenizer 計算長度而非字元數
