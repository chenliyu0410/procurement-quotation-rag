# 固定評測集

`questions.jsonl` 鎖定十種查詢情境，所有測量值目前皆為 `null`、`review_status` 為 `pending`。原先預填的 100% 與毫秒數字沒有實際查詢紀錄支持，已移除。

這個命令是**人工標註彙總器**，不會呼叫模型、不會自動執行題目，也不會判定系統品質達標。`results.json` 中 `null` 表示未量測，`measurement_counts` 顯示實際標註數。零筆標註不會算成 100%。

```bash
python -m app.evaluation.run --dataset evals/questions.jsonl --output evals/results.json
```

正式評測流程：

1. 複製題庫成 `evals/measured.jsonl`，記錄資料快照、模型與索引版本。
2. 逐題呼叫 `/api/query`；對話題需提供實際 `history`，以呼叫端計時取得 `latency_ms`，保存原始問題、response 與 evidence。不要把單元測試速度當作模型延遲。
3. 對照案件、金額、日期、引用及文件頁碼，標註 `structured_correct`、`citations_valid`、`grounded`；不適用的欄位保持 `null`。
4. 每題先列出相關 evidence IDs，再以 Top-5 命中數除以相關總數計算 `recall_at_5`。拒答題標註 `refusal_correct`。
5. 彙總：`python -m app.evaluation.run --dataset evals/measured.jsonl --output evals/measured-results.json`。

比例欄位的分母只包含有標註的題目，P95 只包含有計時的題目。完整評測須另行核對涵蓋率，不能以少量已標註題目推論全部品質。目標為結構化正確率及引用有效率 100%、Recall@5 ≥80%、groundedness ≥90%、拒答正確率 100%、P95 <10 秒；目前尚未取得這些結果。
