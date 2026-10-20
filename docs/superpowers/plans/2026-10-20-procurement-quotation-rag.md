# 採購與報價知識助理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立一個可公開展示的採購與報價知識助理，以 SQL 與向量檢索回答臺北市採購案件、歷史決標金額與採購程序問題，且所有數值及引用可追溯。

**Architecture:** Next.js 前端呼叫 FastAPI；後端將結構化條件送至 PostgreSQL，將語意問題送至 Qdrant，對直接命中的種子片段做相鄰段落擴展，再交由語言模型生成說明。資料擷取以可重入的管理命令執行，PostgreSQL 保存文件 registry 與同步歷史，Qdrant 以版本化 collections 和確定性 point IDs 支援增量索引。

**Tech Stack:** Python、FastAPI、Pydantic、SQLAlchemy、Alembic、PostgreSQL、Qdrant、pytest、Next.js、TypeScript、Vitest、Testing Library、Playwright、Docker Compose。

**Spec:** `docs/superpowers/specs/2026-10-20-procurement-quotation-rag-design.md`

**Current state:** Task 1 was completed and pushed before the Qdrant revision. Its baseline Compose file currently uses a pgvector image; Task 2 replaces that service definition with plain PostgreSQL plus Qdrant before any storage implementation continues.

## Global Constraints

- 公開展示版只使用可公開散布的資料。
- SQL 必須使用參數化查詢；模型不能產生或執行任意 SQL。
- 預算金額與決標金額不得混在同一統計分布。
- 至少 5 個有效歷史決標樣本才顯示第 25 至第 75 百分位參考區間。
- 少於 5 個樣本只列案件並顯示「樣本不足」。
- 回答只能引用本次檢索證據集中存在的 evidence ID。
- 模型與 embedding 金鑰只從後端環境變數讀取。
- 第一版使用手動、可重入的同步命令，不建置常駐排程器。
- 第一版不輸出正式報價單，也不宣稱產生可直接投標的建議價格。
- 案件與文件使用獨立、包含 embedding slug 與 index version 的 Qdrant collections。
- 同一文件或案件重跑同步不得增加重複 vectors。
- 對話只保留最近 2 輪，檢索前先將依賴對話的問題改寫成獨立問題。
- Context 預設 3 個種子片段、前後各 1 個相鄰片段、去重後最多 7 個片段。

## Review Focus

- 來源 CSV 欄位缺失、名稱變更或金額含逗號時，同步應記錄可診斷錯誤，不得靜默寫入錯誤金額；Task 3 測試。
- 中文金額條件包含「萬／億」、民國日期或上下限顛倒時，解析應正確或回傳明確驗證錯誤；Task 5 測試。
- 相似案件少於 5 筆、金額為零、超過近 5 年或預算與決標值混雜時，不得生成參考區間；Task 7 測試。
- 模型回傳不存在的 evidence ID 或改寫來源金額時，API 必須拒絕該引用並使用可驗證資料重建回應；Task 8 測試。
- 月度 resource 消失、案件跨期重複或相同文件重複同步時，歷史案件不得誤刪且 Qdrant point 數不得增加；Task 3 與 Task 4 測試。

---

### Task 1: 建立可啟動的前後端骨架（已完成）

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/tests/test_health.py`
- Create: `frontend/package.json`
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/page.test.tsx`
- Create: `.env.example`
- Create: `compose.yaml`
- Create: `.gitignore`

**Interfaces:**
- Produces: `GET /health -> {"status": "ok"}`。
- Produces: `Settings`，集中讀取 `DATABASE_URL`、`LLM_API_KEY`、`EMBEDDING_MODEL` 與 `LLM_MODEL`。
- Produces: 可啟動的 Next.js 首頁與 FastAPI 服務。

- [ ] **Step 1: 在目前尚非 Git repository 的專案目錄執行 `git init`，確認後續工作可按任務提交**

- [ ] **Step 2: 撰寫後端 health endpoint 的失敗測試**

```python
def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 3: 執行 `cd backend; pytest tests/test_health.py -v`，確認因應用尚未建立而失敗**

- [ ] **Step 4: 建立 `create_app() -> FastAPI`、`GET /health` 與環境設定類別，使測試通過**

- [ ] **Step 5: 撰寫首頁測試，斷言顯示專案名稱、查詢輸入框與一個範例問題**

- [ ] **Step 6: 執行 `cd frontend; npm test -- --run`，確認首頁尚未存在而失敗**

- [ ] **Step 7: 建立最小首頁及 API base URL 設定，使前端測試通過**

- [x] **Step 8: 已建立原始 PostgreSQL/pgvector Compose 基線；新版所需的 Qdrant 轉換移至 Task 2**

- [ ] **Step 9: 執行後端與前端測試，確認全部通過**

- [ ] **Step 10: Commit**

```bash
git add backend frontend .env.example compose.yaml .gitignore
git commit -m "chore: scaffold procurement assistant"
```

### Task 2: 建立採購案件、文件 Registry 與同步紀錄模型

**Files:**
- Modify: `compose.yaml`
- Modify: `.env.example`
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/config.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/models.py`
- Create: `backend/app/db/identity.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial_schema.py`
- Create: `backend/tests/db/test_models.py`

**Interfaces:**
- Produces: `ProcurementCase`、`DocumentRecord`、`DataSource`、`SyncRun` ORM models。
- Produces: `get_session() -> Iterator[Session]`。
- Produces: `Settings.qdrant_url`、`Settings.qdrant_api_key`、`Settings.embedding_provider`、`Settings.index_schema_version`。
- Produces: `build_case_identity(source_dataset, case_number, agency, case_name, year) -> str`。
- `ProcurementCase` 以穩定 identity 唯一識別，保存 raw/normalized category、source period、source row hash 與 active 狀態；金額使用定點 decimal 欄位。
- `DocumentRecord` 保存 version hash、chunk count、embedding provider/model、collection 與 indexed_at。

- [ ] **Step 1: 撰寫設定、模型與 identity 測試，驗證 Qdrant 設定、有案號及無案號的穩定 identity、跨資料集隔離、nullable 金額、raw/normalized category 與 DocumentRecord 索引版本欄位**

- [ ] **Step 2: 執行 `cd backend; pytest tests/db/test_models.py -v`，確認模型尚未定義而失敗**

- [ ] **Step 3: 將 Compose 改為 plain PostgreSQL + Qdrant，加入 qdrant-client/SQLAlchemy/Alembic/psycopg，並建立 Settings、ORM models、identity helper、migration 與必要索引**

- [ ] **Step 4: 執行 migration，並執行模型測試確認通過**

- [ ] **Step 5: Commit**

```bash
git add compose.yaml .env.example backend/pyproject.toml backend/app/config.py backend/app/db backend/alembic.ini backend/alembic backend/tests/db
git commit -m "feat: add procurement data schema"
```

### Task 3: 匯入並正規化兩個官方採購資料集

**Files:**
- Create: `backend/app/ingestion/http.py`
- Create: `backend/app/ingestion/data_taipei.py`
- Create: `backend/app/ingestion/normalize.py`
- Create: `backend/app/ingestion/taxonomy.py`
- Create: `backend/app/ingestion/sync_cases.py`
- Create: `backend/app/cli.py`
- Create: `backend/tests/fixtures/work_bureau.csv`
- Create: `backend/tests/fixtures/metro_tenders.csv`
- Create: `backend/tests/ingestion/test_normalize.py`
- Create: `backend/tests/ingestion/test_sync_cases.py`

**Interfaces:**
- Produces: `parse_money(raw: str | int | None) -> Decimal | None`。
- Produces: `normalize_work_bureau(row: Mapping[str, str]) -> CaseRecord`。
- Produces: `normalize_metro_tender(row: Mapping[str, str]) -> CaseRecord`。
- Produces: `sync_cases(source: SourceConfig, session: Session) -> SyncSummary`，可重跑且不重複寫入。
- Produces: `normalize_category(raw: str, case_name: str) -> NormalizedCategory`，使用版本化固定規則，不呼叫 LLM。
- Produces CLI: `python -m app.cli sync-cases --source work-bureau|metro`。

- [ ] **Step 1: 用固定 fixture 撰寫測試，涵蓋逗號金額、空值、民國年月、缺少必要欄位、欄名變更、taxonomy 映射與未知分類落入其他**

- [ ] **Step 2: 執行 ingestion 測試，確認尚無 parser 而失敗**

- [ ] **Step 3: 實作兩套明確欄位映射與 `CaseRecord`，缺少必要欄位時回傳含來源與欄名的錯誤**

- [ ] **Step 4: 撰寫同步重跑與跨期測試，斷言第二次執行更新既有資料且總筆數不增加、較新 source period 優先、歷史 resource 從清單消失時不刪除案件、完整快照消失項目只做 soft delete**

- [ ] **Step 5: 實作官方資源解析、下載、checksum、upsert 與 `SyncRun` 結果紀錄**

- [ ] **Step 6: 執行 `pytest tests/ingestion -v`，確認所有正常與錯誤案例通過**

- [ ] **Step 7: Commit**

```bash
git add backend/app/ingestion backend/app/cli.py backend/tests/fixtures backend/tests/ingestion
git commit -m "feat: ingest Taipei procurement datasets"
```

### Task 4: 解析採購 PDF 並建立增量 Qdrant 文件索引

**Files:**
- Create: `backend/app/ingestion/pdf.py`
- Create: `backend/app/retrieval/embeddings.py`
- Create: `backend/app/retrieval/qdrant.py`
- Create: `backend/app/retrieval/collections.py`
- Create: `backend/app/ingestion/sync_documents.py`
- Create: `backend/tests/fixtures/procurement_manual_excerpt.pdf`
- Create: `backend/tests/ingestion/test_pdf.py`
- Create: `backend/tests/ingestion/test_sync_documents.py`

**Interfaces:**
- Produces: `extract_pages(pdf_bytes: bytes) -> list[PageText]`，頁碼採一基底。
- Produces: `chunk_pages(pages: Sequence[PageText], max_chars: int, overlap_chars: int) -> list[ChunkInput]`。
- Produces: `EmbeddingProvider.embed(texts: Sequence[str]) -> list[list[float]]` protocol。
- Produces: `collection_name(kind, provider, model, index_version) -> str`。
- Produces: `document_point_id(document_id, version_hash, chunk_index) -> UUID`。
- Produces: `sync_document(source: DocumentSource, embedder: EmbeddingProvider, vectors: VectorIndex, session: Session) -> SyncSummary`。

- [ ] **Step 1: 撰寫 PDF 測試，斷言中文文字、頁碼、chunk 順序與跨頁限制正確**

- [ ] **Step 2: 執行 PDF 測試，確認 parser 尚未建立而失敗**

- [ ] **Step 3: 實作 PDF 逐頁解析與不跨頁 chunking；無文字頁面記錄警告，不在第一版加入 OCR**

- [ ] **Step 4: 以 fake embedder 與 in-memory/fake Qdrant boundary 撰寫同步測試，驗證 hash 未變時不重建、重跑 point 數不增加、內容變更時替換舊版本、同 document/version 才能取得相鄰 chunks**

- [ ] **Step 5: 實作批次 embedding、確定性 Qdrant upsert/delete、版本化 collection/alias 切換與 CLI `sync-documents`**

- [ ] **Step 6: 執行文件 ingestion 測試，確認通過且不呼叫真實付費 API**

- [ ] **Step 7: Commit**

```bash
git add backend/app/ingestion backend/app/retrieval backend/tests/fixtures backend/tests/ingestion
git commit -m "feat: index procurement documents"
```

### Task 5: 解析自然語言條件並執行安全的案件查詢

**Files:**
- Create: `backend/app/search/schemas.py`
- Create: `backend/app/search/query_parser.py`
- Create: `backend/app/search/case_repository.py`
- Create: `backend/tests/search/test_query_parser.py`
- Create: `backend/tests/search/test_case_repository.py`

**Interfaces:**
- Produces: `CaseFilters(agency, category, min_amount, max_amount, start_date, end_date, amount_kind)`。
- Produces: `QueryParser.parse(question: str) -> CaseFilters`；模型輸出必須經 Pydantic 驗證。
- Produces: `CaseRepository.search(filters: CaseFilters, limit: int = 50) -> list[CaseResult]`，只使用預先定義欄位與參數化條件。

- [ ] **Step 1: 撰寫 parser 測試，涵蓋「300 萬到 500 萬」、「一億以下」、民國年月、上下限顛倒與無金額條件**

- [ ] **Step 2: 執行 parser 測試，確認失敗**

- [ ] **Step 3: 實作中文金額正規化、日期轉換、Pydantic 驗證及明確的錯誤型別**

- [ ] **Step 4: 撰寫 repository 測試，斷言金額欄位依 `amount_kind` 選擇、日期邊界包含且不存在任意 SQL 注入路徑**

- [ ] **Step 5: 實作 SQLAlchemy 查詢建構器，使 repository 測試通過**

- [ ] **Step 6: 執行 `pytest tests/search -v`，確認通過**

- [ ] **Step 7: Commit**

```bash
git add backend/app/search backend/tests/search
git commit -m "feat: add safe procurement case search"
```

### Task 6: 建立案件索引、混合式檢索與相鄰段落擴展

**Files:**
- Create: `backend/app/retrieval/schemas.py`
- Create: `backend/app/retrieval/vector_repository.py`
- Create: `backend/app/retrieval/sync_case_vectors.py`
- Create: `backend/app/retrieval/contextual.py`
- Create: `backend/app/retrieval/hybrid.py`
- Create: `backend/tests/retrieval/test_vector_repository.py`
- Create: `backend/tests/retrieval/test_hybrid.py`

**Interfaces:**
- Produces: `Evidence(id, kind, title, text, source_url, page_number, case_id, score, metadata)`。
- Produces: `sync_case_vectors(cases, embedder, vectors) -> SyncSummary`，案件 point ID 使用穩定 identity，內容變更以相同 ID upsert。
- Produces: `VectorRepository.search_cases(query_vector, filters, limit) -> list[Evidence]`。
- Produces: `VectorRepository.search_chunks(query_vector, filters, limit) -> list[Evidence]`。
- Produces: `ContextualRetriever.expand(seeds, window=1, final_k=7) -> list[Evidence]`，種子優先、相鄰片段依距離與種子排名排序。
- Produces: `HybridRetriever.retrieve(question: str, filters: CaseFilters, intent: QueryIntent) -> EvidenceBundle`。

- [ ] **Step 1: 撰寫 Qdrant repository 與案件同步測試，驗證獨立 collections、固定 point ID、內容更新 upsert、inactive 刪除、排序、limit、metadata filter 與 embedding 版本隔離**

- [ ] **Step 2: 執行測試，確認尚未實作而失敗**

- [ ] **Step 3: 實作案件向量同步與案件／文件 Qdrant 查詢**

- [ ] **Step 4: 撰寫 contextual/hybrid 測試，涵蓋種子優先、前後一段、同文件版本隔離、去重、最多 7 段、SQL-only、document-only、combined 與無結果**

- [ ] **Step 5: 實作 ContextualRetriever、intent enum、檢索路由、context budget 及 evidence ID 穩定生成規則**

- [ ] **Step 6: 執行 `pytest tests/retrieval -v`，確認通過**

- [ ] **Step 7: Commit**

```bash
git add backend/app/retrieval backend/tests/retrieval
git commit -m "feat: add hybrid procurement retrieval"
```

### Task 7: 計算歷史決標金額參考區間

**Files:**
- Create: `backend/app/analysis/pricing.py`
- Create: `backend/app/analysis/schemas.py`
- Create: `backend/tests/analysis/test_pricing.py`

**Interfaces:**
- Produces: `select_comparables(target, cases, now, limit=10, years=5) -> list[ComparableCase]`。
- Produces: `build_price_reference(cases: Sequence[ComparableCase]) -> PriceReference`。
- `PriceReference` 包含 `sample_count`、`minimum`、`q1`、`median`、`q3`、`maximum`、`insufficient_sample` 與 `case_ids`。

- [ ] **Step 1: 撰寫失敗測試，驗證相同 normalized category、近 5 年、語意排序前 10 筆，以及 5 筆以上使用 Q1–Q3、decimal 精度與全部輸入 case IDs**

- [ ] **Step 2: 加入少於 5 筆、零／負值、缺少決標金額、只有預算金額與重複案件的失敗測試**

- [ ] **Step 3: 執行 `pytest tests/analysis/test_pricing.py -v`，確認失敗**

- [ ] **Step 4: 實作確定性 percentile 計算；過濾規則必須保留排除原因供 API 顯示**

- [ ] **Step 5: 執行 pricing 測試，確認全部通過**

- [ ] **Step 6: Commit**

```bash
git add backend/app/analysis backend/tests/analysis
git commit -m "feat: calculate historical award ranges"
```

### Task 8: 生成有依據的答案並提供查詢 API

**Files:**
- Create: `backend/app/answering/provider.py`
- Create: `backend/app/answering/prompts.py`
- Create: `backend/app/answering/validator.py`
- Create: `backend/app/answering/service.py`
- Create: `backend/app/answering/query_rewriter.py`
- Create: `backend/app/api/query.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/answering/test_validator.py`
- Create: `backend/tests/api/test_query.py`

**Interfaces:**
- Produces: `AnswerProvider.generate(request: GroundedAnswerRequest) -> DraftAnswer` protocol。
- Produces: `QueryRewriter.rewrite(question: str, history: Sequence[ChatTurn]) -> RewrittenQuery`，history 最多 2 輪並同時保留 original question。
- Produces: `validate_answer(draft: DraftAnswer, evidence: EvidenceBundle) -> ValidatedAnswer`。
- Produces: `POST /api/query`，輸入 `{question: str}`，輸出 answer、cases、price_reference、citations、limitations 與 sync metadata。

- [ ] **Step 1: 撰寫 query rewriter 與 validator 測試，驗證獨立問題不改寫、後續問題使用最多 2 輪歷史、保留原始問題，並拒絕不存在的 evidence ID、來源金額不一致及沒有依據的數值**

- [ ] **Step 2: 執行 validator 測試，確認失敗**

- [ ] **Step 3: 實作問題改寫、結構化模型輸出 schema、引用白名單驗證及由後端證據重建案件與金額欄位**

- [ ] **Step 4: 撰寫 API 測試，使用 fake parser/retriever/provider，涵蓋正常回答、樣本不足、無證據拒答與模型逾時**

- [ ] **Step 5: 實作 query service 與 endpoint；模型逾時時回傳結構化查詢結果及可重試提示**

- [ ] **Step 6: 執行 `pytest tests/answering tests/api -v`，確認通過**

- [ ] **Step 7: Commit**

```bash
git add backend/app/answering backend/app/api backend/app/main.py backend/tests/answering backend/tests/api
git commit -m "feat: add grounded query API"
```

### Task 9: 建立查詢、結果與資料來源介面

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/types/query.ts`
- Create: `frontend/src/components/QueryForm.tsx`
- Create: `frontend/src/components/AnswerPanel.tsx`
- Create: `frontend/src/components/CaseTable.tsx`
- Create: `frontend/src/components/PriceReference.tsx`
- Create: `frontend/src/components/CitationList.tsx`
- Create: `frontend/src/app/sources/page.tsx`
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/components/QueryForm.test.tsx`
- Create: `frontend/src/components/AnswerPanel.test.tsx`
- Create: `frontend/e2e/query.spec.ts`

**Interfaces:**
- Consumes: Task 8 的 `POST /api/query` response。
- Produces: 可輸入範例或自由問題的查詢畫面。
- Produces: 案件比較表、歷史金額區間、限制、同步時間與可點擊引用。

- [ ] **Step 1: 撰寫 QueryForm 測試，驗證空白問題不能送出、送出期間停用按鈕與範例問題可填入**

- [ ] **Step 2: 撰寫 AnswerPanel 測試，驗證正常回答、樣本不足、來源頁碼、可點擊 URL 與部分結果警告**

- [ ] **Step 3: 執行前端單元測試，確認元件尚未建立而失敗**

- [ ] **Step 4: 實作 API client、型別與介面元件，使單元測試通過**

- [ ] **Step 5: 建立資料來源頁，顯示資料集名稱、涵蓋期間、筆數、最近同步與狀態**

- [ ] **Step 6: 撰寫 Playwright 流程，模擬一次成功查詢與一次模型逾時但仍顯示案件的情境**

- [ ] **Step 7: 執行 `cd frontend; npm test -- --run; npx playwright test`，確認通過**

- [ ] **Step 8: Commit**

```bash
git add frontend
git commit -m "feat: build procurement assistant interface"
```

### Task 10: 建立評測、部署與作品集文件

**Files:**
- Create: `backend/evals/questions.jsonl`
- Create: `backend/app/evaluation/run.py`
- Create: `backend/tests/evaluation/test_metrics.py`
- Create: `backend/evals/README.md`
- Create: `Dockerfile.backend`
- Create: `frontend/Dockerfile`
- Create: `README.md`
- Create: `docs/demo-script.md`

**Interfaces:**
- Produces: `python -m app.evaluation.run --dataset evals/questions.jsonl --output evals/results.json`。
- Produces metrics: structured accuracy、citation validity、Recall@5、groundedness、refusal accuracy 與 latency P95。
- Produces: 本機與正式環境部署說明、架構圖、資料來源、限制與面試展示腳本。

- [ ] **Step 1: 撰寫 metrics 測試，使用固定 predictions 驗證每個百分比與 P95 計算**

- [ ] **Step 2: 執行 evaluation 測試，確認尚未實作而失敗**

- [ ] **Step 3: 實作 JSONL schema、評測 runner 與 machine-readable 結果；人工 groundedness 欄位允許後續標註**

- [ ] **Step 4: 建立並人工標註至少 10 題，涵蓋規格列出的六類問題**

- [ ] **Step 5: 執行評測，確認結構化正確率 100%、引用有效率 100%、Recall@5 至少 80%、證據支持率至少 90%、拒答率 100%，並記錄 latency P95**

- [ ] **Step 6: 建立包含 PostgreSQL 與 Qdrant 設定的 production Dockerfiles/部署設定，執行 image build 與容器 health check**

- [ ] **Step 7: 完成 README 與展示腳本，包含環境變數、同步命令、架構、限制、評測結果及公開網址欄位**

- [ ] **Step 8: 執行完整驗證**

```bash
cd backend && pytest -v
cd ../frontend && npm test -- --run && npx playwright test
cd .. && docker compose config
```

Expected: 所有測試通過、Compose 設定有效、公開展示的所有數值與引用可追溯。

- [ ] **Step 9: Commit**

```bash
git add backend/evals backend/app/evaluation backend/tests/evaluation Dockerfile.backend frontend/Dockerfile README.md docs/demo-script.md
git commit -m "docs: add evaluation and deployment guide"
```
