# 使用者輸入到輸出：完整實際流程

![使用者輸入到輸出的完整流程](diagrams/procurement-rag-full-flow.svg)

主圖依使用者實際操作與後端執行順序排列，每一步旁標示所屬教材層級。06A／06B／06C 是替代查詢分支，完成後會合，不是三條都要執行。右上角是資料建置流程；左右橘線是直接回應與部分失敗的路徑。

一口氣講完的順序：使用者輸入 → 前端附上有限對話 → API 檢查請求 → 沿用追問背景 → 解析條件及路由 → 選擇 SQL、相似案件或文件路徑 → 視需要分析價格 → 組成證據 → 判斷是否可生成 → LLM 生成 → 引用與數值驗證 → API 回傳 → 前端呈現 → 使用者收到結果。

教材六層名稱與編號保留不變；[六層責任總覽](diagrams/procurement-rag-six-layers.svg)另存供對照，不把六層硬排成每次請求都走過的六個步驟。

六層是責任分層，不是每次提問依序走 1→6 的六個步驟。資料建置與即時查詢分開閱讀：

- **資料建置：** 1 數據源層 → 2 處理層 → 3 存儲層。新增或更新資料時執行。
- **使用者查詢：** 使用者說明需求 → 6 接入並解析 → 4 檢索增強 → 查詢 3 並取回證據 → 4 組合上下文 → 5 生成 → 6 驗證與呈現 → 使用者收到結果。
- **例外處理：** 無證據或案件價格樣本不足時，由 6 直接回傳限制而略過 5；模型逾時或驗證失敗時保留已查案件。

```mermaid
flowchart TB
    U([01 使用者輸入]) --> WEB[02 前端附上最近兩則對話]
    WEB --> API[03 API 接收與請求驗證]
    API --> REWRITE[04 追問沿用背景]
    REWRITE --> PARSE{05 解析條件與路由}
    PARSE -->|條件案件| SQL[06A PostgreSQL 參數化條件查詢]
    PARSE -->|相似案件或價格| VECTOR[06B 問題 embedding → Qdrant 候選200筆<br/>候選ID再套SQL → 按語意分數排序]
    PARSE -->|文件程序| DOC[06C 問題 embedding → Qdrant 種子3段<br/>前後各1段 → 去重後最多7段]
    SQL --> PRICE[07 價格問題且有分類時<br/>篩選合格樣本、取Top10、至少5筆才產生區間]
    VECTOR --> PRICE
    DOC --> PRICE
    PRICE --> EVIDENCE[08 整理 EvidenceBundle<br/>案件、文件、統計、來源、頁碼與條件]
    EVIDENCE --> GATE{09 可以生成？}
    GATE -->|有證據且未觸發案件價格不足條件| LLM[10 LLM 根據證據生成結構化回答]
    GATE -->|無證據或案件價格樣本不足| DIRECT[直接回覆限制；保留可用案件]
    LLM --> VALIDATE[11 驗證引用與數值，還原網址及頁碼]
    LLM -->|逾時或模型API錯誤| PARTIAL[保留案件與價格狀態，標示partial]
    VALIDATE -->|通過| RESPONSE[12 API 回傳]
    VALIDATE -->|未通過| PARTIAL
    DIRECT --> RESPONSE
    PARTIAL --> RESPONSE
    RESPONSE --> VIEW[13 前端顯示摘要、案件表、價格狀態、引用與限制]
    VIEW --> OUT([14 使用者收到結果，可繼續追問])
    SOURCE[事前：第1層 官方API／CSV／PDF] -.-> PROCESS[第2層 清洗、解析、切片、向量化]
    PROCESS -.-> STORE[第3層 PostgreSQL／Qdrant]
    STORE -. 供查詢 .-> SQL
    STORE -. 供查詢 .-> VECTOR
    STORE -. 供查詢 .-> DOC
```

| 教材六層 | 本專案已實作 | 對應程式 |
| --- | --- | --- |
| 6. 應用與運維管控層 | Web／API、有限對話、需求解析與路由、來源狀態、引用與數值驗證、逾時回退、測試及評測紀錄 | `frontend/src/app/`、`backend/app/api/`、`backend/app/answering/service.py`、`query_rewriter.py`、`validator.py`、`backend/app/search/query_parser.py` |
| 5. 生成層 | 根據本次證據生成摘要，結構化輸出限制可引用的 evidence ID | `backend/app/answering/openai.py`、`provider.py`、`prompts.py` |
| 4. 檢索增強層 | 條件 SQL、向量候選再 SQL、相似分數排序、相鄰段落擴展與去重、context 上限、合格價格樣本與確定性統計 | `backend/app/runtime.py`、`backend/app/search/case_repository.py`、`backend/app/retrieval/vector_repository.py`、`contextual.py`、`backend/app/analysis/pricing.py` |
| 3. 存儲層 | PostgreSQL 案件、來源與同步紀錄；Qdrant 案件及文件向量；保存來源／頁碼／版本等中繼資料 | `backend/app/db/`、`backend/app/retrieval/qdrant.py`、`collections.py` |
| 2. 處理層 | API／CSV 正規化、民國日期及金額解析、PDF 切分、embedding、內容雜湊、可重跑同步 | `backend/app/ingestion/`、`backend/app/retrieval/embeddings.py`、`backend/app/cli.py` |
| 1. 數據源層 | 工務局與捷運公開採購資料；工程會兩份程序文件 | README 資料來源、`docs/procedure-sources.json` |

**教材能力與目前實作的界線：** 教材列出企業級完整能力，本作品目前是本機公開資料展示。尚無獨立 reranker、權限控制／權限標籤、正式監控告警及自動知識更新；已提供來源狀態、基本服務健康檢查、測試與人工啟動同步。不能將六層都畫出來解讀為教材每項能力都已實作。

面試說明：「使用者從第六層的 Web／API 說明需求，系統解析條件後交給第四層查詢第三層。第四層把案件或文件整理成上下文，送第五層生成摘要，再回第六層做引用及數值驗證，最後輸出給使用者。底下的一到三層則是事前把官方資料清洗、切片、向量化並保存的流程。」

六層是邏輯責任，不是六個獨立服務；同一模組可能承擔多層職責。條件案件可直接查 SQL，不會全部都做 embedding；引用與數值驗證不代表完整語意正確。
