# 採購與報價知識助理

以臺北市資料大平臺公開採購資料建立的作品集 RAG 專案。系統將可驗證的 SQL 條件查詢、Qdrant 語意搜尋、採購文件問答與歷史決標金額統計放在同一個介面，回答中的案件、金額與文件頁碼都必須能追溯來源。

目前已匯入並索引工務局 1,043 筆決標紀錄、捷運公司 52 筆預算案件，以及工程會兩份採購程序文件的 22 個段落。本機展示已啟動，見[啟動與驗收說明](docs/local-demo.md)及[五分鐘展示流程](docs/demo-script.md)。原十題已完成真實呼叫與作者／代理檢查，兩題文件問題未通過語意檢查；獨立人工驗收、完整相關標註、有日期的價格樣本及公開部署仍待完成。詳細交接見 [docs/progress.md](docs/progress.md)。

## 能力展示

- 兩套公開 CSV adapter、民國日期與金額正規化、固定 taxonomy、跨期去重與 soft delete。
- PostgreSQL 保存結構化案件；Qdrant 分開保存案件與文件向量，collection 隨 provider、model、schema 版本隔離。
- 文件以內容雜湊增量同步，point ID 由文件、版本與 chunk 序號確定性產生。
- 自然語言條件轉成 Pydantic schema，再由 SQLAlchemy 參數化查詢。
- 價格區間只採同分類、近五年、有效決標金額的語意 Top-10；至少五筆才計算 Q1–Q3。
- 回答只接受本次 evidence ID，後端檢查引用與數字是否存在於所引用證據；無證據時拒答。這不等同完整的語意事實驗證。

![使用者輸入到輸出的完整流程](docs/diagrams/procurement-rag-full-flow.svg)

六層沿用教材定義，由上而下為：⑥應用與運維管控層、⑤生成層、④檢索增強層、③存儲層、②處理層、①數據源層。

使用者查詢：輸入 → 前端附上對話 → API 檢查 → 追問背景 → 條件解析及路由 → SQL／相似案件／文件檢索 → 價格分析 → 整理證據 → 判斷是否生成 → 模型生成 → 後端驗證 → API 回傳 → 前端呈現 → 使用者收到結果。無證據、價格樣本不足及模型失敗另有回應路徑。完整分支圖、教材層級與程式對應見 [完整架構流程](docs/architecture.md)。

## 本機啟動

需求：Python 3.12+、Node.js 22+、Docker。

```bash
cp .env.example .env
cp .env backend/.env
docker compose up -d database qdrant
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --env-file ../.env
```

另一個終端：

```bash
cd frontend
npm ci
npm run dev
```

本機 PostgreSQL 對外使用 `55432`，避免常見的既有 `5432` 服務衝突。設定 `LLM_API_KEY`、`LLM_MODEL`、`EMBEDDING_MODEL` 後，可執行：

```bash
python -m app.cli sync-cases --source work-bureau --resource-url <官方CSV下載網址> --period 2026
python -m app.cli sync-case-vectors
python -m app.cli sync-documents <採購手冊.pdf> --document-id procurement-manual --source-url <官方網址>
```

也可直接同步官方 JSON API，無需手動下載 CSV：

```bash
python -m app.cli sync-cases --source work-bureau --format api --resource-url "https://data.taipei/api/v1/dataset/a064da04-bfe4-4677-a04e-fe95eeb81fa3?scope=resourceAquire" --period 2026-05 --dry-run
python -m app.cli sync-cases --source work-bureau --format api --resource-url "https://data.taipei/api/v1/dataset/a064da04-bfe4-4677-a04e-fe95eeb81fa3?scope=resourceAquire" --period 2026-05
```

API reader 以 `limit=1000`、`offset` 與 `_id` 排序完整分頁下載，再進行正規化與交易寫入；空頁、重複列、筆數異動或 HTTP 錯誤會中止同步。`--dry-run` 不連接資料庫。系統憑證庫負責 TLS 驗證，且不跟隨重新導向。`--period` 是來源快照期別，不是決標日期。

捷運公司 2026-10 官方 API 亦可直接同步，並只為該來源建立向量：

```bash
python -m app.cli sync-cases --source metro --format api --resource-url "https://data.taipei/api/v1/dataset/69fe3257-3e97-4386-8a8c-f760586f5be9?scope=resourceAquire" --period 2026-10
python -m app.cli sync-case-vectors --source metro
```

實測匯入 52 筆，重跑異動 0 筆，其中 20 筆「預算金額不公開」保留 null。原始資料沒有正式案號與實際招標／決標日期；序號不當案號，統計期只顯示為來源期別。捷運資料沿用機關、名稱與年度識別，不使用會隨每月資源更換的 API 列 ID。介面分開顯示預算與決標金額。

2026-10-21 實測上述資源為 1,043 筆決標紀錄；相同案號可能屬於不同機關或多筆決標，因此 API 列採 `resource_id + _id` 識別並保留原始案號，重跑相同快照不增加筆數。平台重新匯入時若重編 `_id`，仍需人工比對；這不是跨資源／跨期的自然案件主鍵。這支 API 沒有決標日期，全部維持空值，不能用 `_importdate` 冒充，因此這批資料不能直接支援「近五年決標金額」統計。多筆決標紀錄也不能當成獨立標案做價格樣本。

上述 CLI 與 Alembic 會讀取工作目錄中的 `.env`。在 `backend/` 執行時，請先把根目錄 `.env` 複製到 `backend/.env`，或以 shell 設定環境變數。同步文件與案件向量會呼叫設定的 embedding API；`EMBEDDING_DIMENSION` 預設為 1536，文件命令的 `--dimension` 必須與查詢使用的設定相同。尚未設定模型時，查詢 API 會回傳 `configuration_required`。

模型 adapter 依 [OpenAI Structured Outputs 文件](https://developers.openai.com/api/docs/guides/structured-outputs) 使用 Responses API JSON schema；請選擇帳號可使用且支援該格式的模型。

推理模型可選填 `LLM_REASONING_EFFORT`，留空時不傳送此參數。這次本機 `gpt-5-mini` 使用 `minimal`，以降低簡短查詢的等待時間；不同模型的可用值不同，見 [OpenAI 官方更新紀錄](https://developers.openai.com/api/docs/changelog)。引用 schema 只允許當次 evidence ID，仍會執行後端白名單與數值驗證。

## Docker 啟動

在專案根目錄準備 `.env` 後：

```bash
docker compose --profile app up -d --build
docker compose exec backend python -m app.cli sync-cases --source work-bureau --resource-url <官方CSV下載網址> --period 2026
docker compose exec backend python -m app.cli sync-case-vectors
```

前端：`http://localhost:3000`，API 文件：`http://localhost:8000/docs`。後端啟動時會執行資料庫 migration。文件同步需先將 PDF 放進容器，例如 `docker compose cp manual.pdf backend:/tmp/manual.pdf`，再執行 `sync-documents /tmp/manual.pdf ...`。

部署到其他主機時，必須修改 `NEXT_PUBLIC_API_BASE_URL` 為瀏覽器可連線的 API 網址並重建前端 image；修改 `CORS_ORIGINS` JSON 陣列為正式前端來源。此 Compose 使用本機開發用帳密及連接埠，公開部署仍需設定正式資料庫憑證、反向代理與存取控制。

## 驗證

```bash
cd backend && pytest -v
python -m app.evaluation.run --dataset evals/questions.jsonl --output evals/results.json
cd ../frontend && npm test -- --run && npm run build
cd .. && docker compose --profile app config --quiet
```

固定題庫包含 10 題，涵蓋金額與日期、相似案件、價格統計、文件問答、對話與拒答。runner 只彙總標註，不會執行查詢；未量測欄位輸出 `null`，並顯示每項指標的標註筆數。本機真實十題紀錄及作者／代理檢查見 [local-demo-review.json](backend/evals/local-demo-review.json)：groundedness 8/10，尚未達原定門檻，Recall@5 未量測；十次呼叫的延遲不能代表正式公開服務 P95。操作方式見 [backend/evals/README.md](backend/evals/README.md)。

GitHub Actions 會執行後端測試、前端測試、正式建置、Compose 設定驗證與後端 image build；CI 不需模型金鑰。

## 資料來源

- [臺北市政府工務局採購案件](https://data.taipei/dataset/detail?id=2be36284-8463-495c-bcff-fc45d403efac)
- [臺北捷運公司採購案件預定招標時程](https://data.taipei/dataset/detail?id=f4fd7f03-9bf6-41de-a003-02c437596570)
- [工程會採購業務標準作業流程](https://www.pcc.gov.tw/content/index?eid=1740&type=C)：JP01「未經公告程序之限制性招標」（2024-10-18，6 頁）與 JP03「開標作業」（2021-12，5 頁），分別索引 12、10 個段落。

程序文件來源為行政院公共工程委員會，依其[網站資料開放宣告](https://www.pcc.gov.tw/content/cp.aspx?n=8EAE57B03C93D280)標示出處。下載網址、版本與 SHA-256 見 [procedure-sources.json](docs/procedure-sources.json)。PDF 保存在本機 `data/documents/`，未放入 Git；依 manifest 下載後，可用 `sync-documents <PDF路徑> --document-id pcc-jp01 --source-url <manifest中的網址>` 同步，JP03 同理。相同內容重跑會略過 embedding。文件引用連結會附帶 `#page=` 頁碼。

原規劃的臺北市採購手冊資源是 2012 年版且明列限制再利用，本次改用上述工程會文件。回答僅依已索引版本，不保證涵蓋現行法令的所有修正。

## 限制

公開資料通常缺少規格、數量、工期與風險條件，因此價格結果只稱為「歷史決標金額參考區間」，不能作為正式投標報價。掃描 PDF 第一版不做 OCR。語意查詢先從全體向量取最多 200 筆候選，再由 SQL 套用硬條件與有效狀態，最後依相似度排序；不再先截斷 SQL 前 200 筆。較嚴格的硬條件仍可能因向量候選上限而漏掉結果。價格查詢需指定分類。引用驗證無法保證每句敘述及數字與案件的語意對應正確，仍需人工評測。正式公開網址：`待部署後補上`。

面試展示步驟見 [docs/demo-script.md](docs/demo-script.md)，設計與完整實作計畫位於 `docs/superpowers/`。
