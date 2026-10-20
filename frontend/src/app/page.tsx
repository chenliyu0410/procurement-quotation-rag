"use client";
import { useState } from "react";
import { AnswerPanel } from "../components/AnswerPanel";
import { QueryForm } from "../components/QueryForm";
import { queryProcurement } from "../lib/api";
import type { QueryResponse } from "../types/query";

export default function Home() {
  const [result, setResult] = useState<QueryResponse | null>(null); const [loading, setLoading] = useState(false);
  async function query(question: string) { setLoading(true); try { setResult(await queryProcurement(question)); } catch { setResult({ answer: "查詢服務暫時無法使用。", cases: [], price_reference: null, citations: [], limitations: ["請確認後端服務與網路連線。"], sync_metadata: { status: "error" } }); } finally { setLoading(false); } }
  return (
    <main className="app-shell"><nav><strong>採購知識簿</strong><a href="/sources">資料來源</a></nav><header className="masthead"><p>臺北市公開採購資料</p><h1>採購與報價知識助理</h1><span>用可追溯的案件與文件，整理需求、比較歷史決標金額。</span></header><div className="workspace"><aside><QueryForm onQuery={query} loading={loading}/></aside><section className="results"><AnswerPanel result={result}/></section></div>
    </main>
  );
}
