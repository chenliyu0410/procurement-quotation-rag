"use client";
import { useEffect, useState } from "react";

type Source = { id: string; name: string; period: string; status: string; record_count: number; last_synced_at: string | null };

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [message, setMessage] = useState("讀取資料來源中…");
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/sources`, { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error(); return response.json(); })
      .then(data => { setSources(data.sources); setMessage(data.sources.length ? "" : "尚未同步任何資料。"); })
      .catch(() => { if (!controller.signal.aborted) setMessage("無法讀取同步狀態，請確認後端與資料庫服務。"); });
    return () => controller.abort();
  }, []);
  return <main className="sources-page"><a href="/">返回查詢</a><h1>資料來源與狀態</h1><p>所有回答都應能連回公開資料或文件頁碼。</p>{message && <p role="status">{message}</p>}<div className="source-list">{sources.map(source => <article key={source.id}><h2>{source.name}</h2><dl><dt>涵蓋期間／版本</dt><dd>{source.period}</dd><dt>案件／文字段落筆數</dt><dd>{source.record_count}</dd><dt>最近同步</dt><dd>{source.last_synced_at ?? "未提供"}</dd><dt>狀態</dt><dd>{source.status}</dd></dl></article>)}</div></main>;
}
